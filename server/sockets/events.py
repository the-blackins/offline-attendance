"""
WebSocket event handlers for real-time communication.
"""
from flask_socketio import emit, join_room, leave_room
from flask import request


def register_socket_events(socketio):
    """Register all WebSocket event handlers with the SocketIO instance."""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        client_id = request.sid
        print(f"[WS] Client connected: {client_id}")
        emit('connected', {'message': 'Connected to attendance server', 'sid': client_id})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        client_id = request.sid
        print(f"[WS] Client disconnected: {client_id}")

    @socketio.on('join_session')
    def handle_join_session(data):
        """
        Client joins a session room for real-time updates.
        Data: { "session_token": "abc123" }
        """
        session_token = data.get('session_token', '')
        if session_token:
            join_room(f"session_{session_token}")
            emit('joined_session', {
                'message': f'Joined session room',
                'session_token': session_token
            })
            print(f"[WS] Client {request.sid} joined session_{session_token}")

    @socketio.on('leave_session')
    def handle_leave_session(data):
        """Client leaves a session room."""
        session_token = data.get('session_token', '')
        if session_token:
            leave_room(f"session_{session_token}")
            print(f"[WS] Client {request.sid} left session_{session_token}")

    @socketio.on('join_lecturer')
    def handle_join_lecturer(data):
        """Lecturer joins the lecturer room for dashboard updates."""
        join_room('lecturer_dashboard')
        emit('joined_lecturer', {'message': 'Connected to lecturer dashboard'})
        print(f"[WS] Lecturer dashboard connected: {request.sid}")

    @socketio.on('check_in')
    def handle_check_in(data):
        """
        Real-time check-in via WebSocket.
        Data: { "student_id": "...", "device_uuid": "...", "session_token": "..." }
        """
        from models import Student, Session as AttSession, Attendance, SyncQueue
        from database import db
        from datetime import datetime
        from flask import current_app

        student_id = data.get('student_id', '').strip()
        device_uuid = data.get('device_uuid', '').strip()
        session_token = data.get('session_token', '').strip()

        if not student_id or not device_uuid or not session_token:
            emit('check_in_response', {
                'success': False,
                'error': 'Missing required fields'
            })
            return

        # Validation pipeline
        session = AttSession.query.filter_by(session_token=session_token).first()
        if not session or not session.is_active:
            emit('check_in_response', {
                'success': False,
                'error': 'No active session with this token'
            })
            return

        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            emit('check_in_response', {
                'success': False,
                'error': 'Student not enrolled'
            })
            return

        if student.device_uuid != device_uuid:
            emit('check_in_response', {
                'success': False,
                'error': 'Device mismatch'
            })
            return

        existing = Attendance.query.filter_by(
            student_id=student.id,
            session_id=session.id
        ).first()

        if existing:
            emit('check_in_response', {
                'success': False,
                'error': 'Already checked in',
                'attendance': existing.to_dict()
            })
            return

        # Determine status
        late_threshold = current_app.config.get('LATE_THRESHOLD_MINUTES', 15)
        now = datetime.utcnow()
        status = 'present'
        if session.start_time:
            minutes_since_start = (now - session.start_time).total_seconds() / 60
            if minutes_since_start > late_threshold:
                status = 'late'

        # Record attendance
        attendance = Attendance(
            student_id=student.id,
            session_id=session.id,
            status=status
        )
        db.session.add(attendance)
        db.session.commit()

        # Queue for sync
        sync_entry = SyncQueue(table_name='attendance', record_id=attendance.id)
        db.session.add(sync_entry)
        db.session.commit()

        # Notify the student
        emit('check_in_response', {
            'success': True,
            'message': f'Attendance recorded as {status}',
            'attendance': attendance.to_dict()
        })

        # Broadcast to lecturer dashboard
        socketio.emit('attendance_update', {
            'attendance': attendance.to_dict(),
            'session': session.to_dict()
        }, room='lecturer_dashboard')

        # Broadcast to session room
        socketio.emit('session_attendance_count', {
            'session_id': session.id,
            'count': Attendance.query.filter_by(session_id=session.id).count()
        }, room=f"session_{session_token}")

        print(f"[WS] Check-in: {student_id} → {status}")

    @socketio.on('heartbeat')
    def handle_heartbeat(data):
        """
        Optional heartbeat to verify student presence.
        Data: { "student_id": "...", "session_token": "..." }
        """
        emit('heartbeat_ack', {'status': 'alive', 'timestamp': data.get('timestamp')})

    return socketio
