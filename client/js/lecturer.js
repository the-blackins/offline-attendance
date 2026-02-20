/**
 * Lecturer dashboard logic.
 */
const LecturerApp = (() => {
    let isAuthenticated = false;
    let activeSession = null;
    let attendanceRecords = [];

    function $(sel) { return document.querySelector(sel); }
    function $$(sel) { return document.querySelectorAll(sel); }

    function showAlert(message, type = 'info') {
        const container = $('#alert-container');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `<span>${message}</span>`;
        container.prepend(alert);
        setTimeout(() => alert.remove(), 5000);
    }

    function showScreen(name) {
        $$('.screen').forEach(s => s.classList.remove('active'));
        const screen = $(`#screen-${name}`);
        if (screen) screen.classList.add('active');
    }

    function updateConnectionStatus(connected) {
        const el = $('#connection-status');
        if (connected) {
            el.className = 'status-indicator connected';
            el.innerHTML = '<span class="status-dot"></span> Connected';
        } else {
            el.className = 'status-indicator disconnected';
            el.innerHTML = '<span class="status-dot"></span> Disconnected';
        }
    }

    // ─── Login ───
    async function handleLogin(e) {
        e.preventDefault();
        const password = $('#login-password').value;

        try {
            const res = await fetch('/api/lecturer/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });
            const data = await res.json();

            if (res.ok) {
                isAuthenticated = true;
                showScreen('dashboard');
                loadDashboard();

                // Join lecturer room for real-time updates
                SocketManager.emit('join_lecturer', {});
            } else {
                showAlert(data.error || 'Login failed', 'error');
            }
        } catch (err) {
            showAlert('Connection error', 'error');
        }
    }

    // ─── Dashboard ───
    async function loadDashboard() {
        await checkActiveSession();
        await loadStudents();
    }

    async function checkActiveSession() {
        try {
            const res = await fetch('/api/session/active');
            const data = await res.json();

            if (data.active) {
                activeSession = data.session;
                updateSessionUI(true);
                loadAttendance(activeSession.id);
                loadQR();
            } else {
                activeSession = null;
                updateSessionUI(false);
            }
        } catch (err) {
            console.warn('Could not check session:', err);
        }
    }

    function updateSessionUI(active) {
        if (active && activeSession) {
            $('#session-display').innerHTML = `
        <div class="session-banner">
          <div class="course-code">${activeSession.course_code}</div>
          <div class="session-status">🟢 Session Active • ${activeSession.attendance_count || 0} checked in</div>
        </div>
      `;
            $('#btn-start-session').style.display = 'none';
            $('#btn-end-session').style.display = 'block';
            $('#session-course-code').value = activeSession.course_code;
        } else {
            $('#session-display').innerHTML = `
        <div class="empty-state" style="padding: 20px;">
          <div class="icon">📭</div>
          <div class="message">No active session</div>
        </div>
      `;
            $('#btn-start-session').style.display = 'block';
            $('#btn-end-session').style.display = 'none';
        }
    }

    // ─── Session Controls ───
    async function startSession() {
        const courseCode = $('#session-course-code').value.trim();
        if (!courseCode) {
            showAlert('Enter a course code', 'warning');
            return;
        }

        try {
            const res = await fetch('/api/session/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ course_code: courseCode })
            });
            const data = await res.json();

            if (res.ok) {
                activeSession = data.session;
                updateSessionUI(true);
                loadQR();
                showAlert(`Session started for ${courseCode}`, 'success');

                // Broadcast to all connected clients
                SocketManager.emit('session_update', {
                    action: 'started',
                    session: activeSession
                });
            } else {
                showAlert(data.error, 'error');
            }
        } catch (err) {
            showAlert('Failed to start session', 'error');
        }
    }

    async function endSession() {
        if (!activeSession) return;

        try {
            const res = await fetch('/api/session/end', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: activeSession.id })
            });
            const data = await res.json();

            if (res.ok) {
                showAlert(`Session ended. ${activeSession.attendance_count || 0} attendance records.`, 'success');

                SocketManager.emit('session_update', {
                    action: 'ended',
                    session: data.session
                });

                activeSession = null;
                updateSessionUI(false);
                $('#qr-display').innerHTML = '';
                attendanceRecords = [];
                renderAttendanceTable();
            } else {
                showAlert(data.error, 'error');
            }
        } catch (err) {
            showAlert('Failed to end session', 'error');
        }
    }

    // ─── QR Code ───
    async function loadQR() {
        if (!activeSession) return;

        try {
            const res = await fetch(`/api/session/qr?course_code=${activeSession.course_code}`);
            const data = await res.json();

            if (res.ok) {
                $('#qr-display').innerHTML = `
          <img src="${data.qr_code}" alt="Session QR Code" />
          <p style="margin-top: 8px; font-size: 0.8rem; color: var(--text-muted);">
            Token: ${data.session_token.substring(0, 12)}...
          </p>
        `;
            }
        } catch (err) {
            console.warn('Could not load QR:', err);
        }
    }

    // ─── Attendance ───
    async function loadAttendance(sessionId) {
        try {
            const res = await fetch(`/api/attendance/${sessionId}`);
            const data = await res.json();

            if (res.ok) {
                attendanceRecords = data.attendance;
                renderAttendanceTable();
                updateStats(data);
            }
        } catch (err) {
            console.warn('Could not load attendance:', err);
        }
    }

    function renderAttendanceTable() {
        const tbody = $('#attendance-tbody');
        if (!tbody) return;

        if (attendanceRecords.length === 0) {
            tbody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 24px;">
            No attendance records yet
          </td>
        </tr>
      `;
            return;
        }

        tbody.innerHTML = attendanceRecords.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><strong>${r.student_name || 'Unknown'}</strong><br>
            <span style="font-size: 0.8rem; color: var(--text-muted);">${r.student_matric || ''}</span></td>
        <td>${new Date(r.timestamp).toLocaleTimeString()}</td>
        <td><span class="badge badge-${r.status}">${r.status}</span></td>
      </tr>
    `).join('');
    }

    function updateStats(data) {
        $('#stat-total').textContent = data.attendance.length;
        $('#stat-present').textContent = data.total_present || 0;
        $('#stat-late').textContent = data.total_late || 0;
    }

    // ─── Students ───
    async function loadStudents() {
        try {
            const res = await fetch('/api/students');
            const data = await res.json();

            if (res.ok) {
                const container = $('#students-list');
                if (data.students.length === 0) {
                    container.innerHTML = '<div class="empty-state"><div class="message">No enrolled students</div></div>';
                    return;
                }

                container.innerHTML = data.students.map(s => `
          <div class="card" style="padding: 14px 18px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong>${s.name}</strong>
                <div style="font-size: 0.8rem; color: var(--text-muted);">${s.student_id}</div>
              </div>
              <span class="badge badge-present">Enrolled</span>
            </div>
          </div>
        `).join('');
            }
        } catch (err) {
            console.warn('Could not load students:', err);
        }
    }

    // ─── Tab Navigation ───
    function switchTab(tabName) {
        $$('.nav-tab').forEach(t => t.classList.remove('active'));
        $(`[data-tab="${tabName}"]`).classList.add('active');

        $$('.tab-content').forEach(t => t.style.display = 'none');
        $(`#tab-${tabName}`).style.display = 'block';
    }

    // ─── WebSocket Listeners ───
    function setupSocketListeners() {
        SocketManager.on('connectionChange', updateConnectionStatus);

        SocketManager.on('attendance_update', (data) => {
            if (activeSession && data.session.id === activeSession.id) {
                attendanceRecords.push(data.attendance);
                activeSession.attendance_count = attendanceRecords.length;
                renderAttendanceTable();
                updateSessionUI(true);
                updateStats({
                    attendance: attendanceRecords,
                    total_present: attendanceRecords.filter(r => r.status === 'present').length,
                    total_late: attendanceRecords.filter(r => r.status === 'late').length,
                });
            }
        });
    }

    // ─── Init ───
    function init() {
        SocketManager.connect();
        setupSocketListeners();

        showScreen('login');

        // Event bindings
        $('#form-login').addEventListener('submit', handleLogin);
        $('#btn-start-session').addEventListener('click', startSession);
        $('#btn-end-session').addEventListener('click', endSession);

        // Tab navigation
        $$('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });
    }

    return { init };
})();

document.addEventListener('DOMContentLoaded', LecturerApp.init);
