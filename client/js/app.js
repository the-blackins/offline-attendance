/**
 * Student-side application logic.
 */
const App = (() => {
    // State
    let currentScreen = 'enrollment';
    let studentData = null;
    let activeSession = null;

    // ─── DOM Helpers ───
    function $(sel) { return document.querySelector(sel); }
    function $$(sel) { return document.querySelectorAll(sel); }

    function showScreen(name) {
        $$('.screen').forEach(s => s.classList.remove('active'));
        const screen = $(`#screen-${name}`);
        if (screen) {
            screen.classList.add('active');
            currentScreen = name;
        }
    }

    function showAlert(message, type = 'info') {
        const container = $('#alert-container');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `<span>${message}</span>`;
        container.prepend(alert);

        setTimeout(() => alert.remove(), 5000);
    }

    function updateStatus(connected) {
        const indicator = $('#connection-status');
        if (connected) {
            indicator.className = 'status-indicator connected';
            indicator.innerHTML = '<span class="status-dot"></span> Connected';
        } else {
            indicator.className = 'status-indicator disconnected';
            indicator.innerHTML = '<span class="status-dot"></span> Disconnected';
        }
    }

    // ─── Enrollment ───
    async function handleEnroll(e) {
        e.preventDefault();

        const studentId = $('#enroll-student-id').value.trim();
        const name = $('#enroll-name').value.trim();
        const pin = $('#enroll-pin').value.trim();

        if (!studentId || !name) {
            showAlert('Student ID and Name are required', 'error');
            return;
        }

        const deviceUuid = DeviceUUID.get();
        const btn = $('#btn-enroll');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Enrolling...';

        try {
            const res = await fetch('/api/enroll', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: studentId,
                    name: name,
                    device_uuid: deviceUuid,
                    pin: pin || null
                })
            });

            const data = await res.json();

            if (res.ok) {
                studentData = data.student;
                localStorage.setItem('student_data', JSON.stringify(studentData));
                showAlert('Enrollment successful! ✅', 'success');
                showScreen('checkin');
                checkForActiveSession();
            } else {
                showAlert(data.error || 'Enrollment failed', 'error');
            }
        } catch (err) {
            showAlert('Network error. Make sure you are connected to the server.', 'error');
        }

        btn.disabled = false;
        btn.innerHTML = '📝 Enroll';
    }

    // ─── Check for Active Session ───
    async function checkForActiveSession() {
        try {
            const res = await fetch('/api/session/active');
            const data = await res.json();

            if (data.active && data.session) {
                activeSession = data.session;
                updateSessionDisplay(activeSession);
                $('#btn-checkin').disabled = false;
            } else {
                activeSession = null;
                updateSessionDisplay(null);
                $('#btn-checkin').disabled = true;
            }
        } catch (err) {
            console.warn('Could not check session:', err);
        }
    }

    function updateSessionDisplay(session) {
        const banner = $('#session-info');
        if (session) {
            banner.innerHTML = `
        <div class="course-code">${session.course_code}</div>
        <div class="session-status">📡 Session active • ${session.attendance_count || 0} checked in</div>
      `;
            banner.style.display = 'block';
        } else {
            banner.innerHTML = `
        <div class="session-status">No active session</div>
      `;
        }
    }

    // ─── Check In ───
    async function handleCheckIn() {
        if (!studentData || !activeSession) {
            showAlert('No active session or not enrolled.', 'warning');
            return;
        }

        const btn = $('#btn-checkin');
        btn.disabled = true;

        // Use WebSocket for real-time check-in
        SocketManager.emit('check_in', {
            student_id: studentData.student_id,
            device_uuid: DeviceUUID.get(),
            session_token: activeSession.session_token
        });
    }

    // ─── WebSocket Handlers ───
    function setupSocketListeners() {
        SocketManager.on('connectionChange', (connected) => {
            updateStatus(connected);
            if (connected && currentScreen === 'checkin') {
                checkForActiveSession();
            }
        });

        SocketManager.on('check_in_response', (data) => {
            const btn = $('#btn-checkin');
            if (data.success) {
                showAlert(data.message, 'success');
                btn.disabled = true;
                btn.querySelector('.icon').textContent = '✅';
                btn.querySelector('.label').textContent = 'Checked In';
            } else {
                showAlert(data.error, 'error');
                btn.disabled = false;
            }
        });

        SocketManager.on('session_update', (data) => {
            if (data.action === 'started') {
                activeSession = data.session;
                updateSessionDisplay(activeSession);
                $('#btn-checkin').disabled = false;
                showAlert(`Session started for ${data.session.course_code}`, 'info');
            } else if (data.action === 'ended') {
                activeSession = null;
                updateSessionDisplay(null);
                $('#btn-checkin').disabled = true;
                showAlert('Session ended', 'info');
            }
        });

        SocketManager.on('session_attendance_count', (data) => {
            if (activeSession && data.session_id === activeSession.id) {
                activeSession.attendance_count = data.count;
                updateSessionDisplay(activeSession);
            }
        });
    }

    // ─── Init ───
    function init() {
        // Connect WebSocket
        SocketManager.connect();
        setupSocketListeners();

        // Check if already enrolled
        const saved = localStorage.getItem('student_data');
        if (saved) {
            studentData = JSON.parse(saved);
            showScreen('checkin');
            checkForActiveSession();
        } else {
            showScreen('enrollment');
        }

        // Event bindings
        $('#form-enroll').addEventListener('submit', handleEnroll);
        $('#btn-checkin').addEventListener('click', handleCheckIn);
        $('#btn-logout').addEventListener('click', () => {
            localStorage.removeItem('student_data');
            studentData = null;
            showScreen('enrollment');
        });

        // Poll for active session every 10s
        setInterval(checkForActiveSession, 10000);
    }

    return { init };
})();

// Start the app
document.addEventListener('DOMContentLoaded', App.init);
