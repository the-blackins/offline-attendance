"""
Attendance routes: check-in, validation pipeline, manual overrides.
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from database import db
from models import Student, Session, Attendance, SyncQueue

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/api/check-in', methods=['POST'])
def check_in():
    """
    Student submits attendance for the active session.
    
    Expects JSON:
    {
        "student_id": "CSC/2023/001",
        "device_uuid": "abc-123-def-456",
        "session_token": "xyz789..."
    }
    
    Validation pipeline:
    1. Session active?
    2. Token valid?
    3. Device matches student?
    4. Student not already marked?
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    student_id = data.get('student_id', '').strip()
    device_uuid = data.get('device_uuid', '').strip()
    session_token = data.get('session_token', '').strip()

    if not student_id or not device_uuid or not session_token:
        return jsonify({'error': 'student_id, device_uuid, and session_token are required'}), 400

    # Step 1: Find the session and check if it's active
    session = Session.query.filter_by(session_token=session_token).first()
    if not session:
        return jsonify({'error': 'Invalid session token'}), 404

    if not session.is_active:
        return jsonify({'error': 'Session has ended'}), 403

    # Step 2: Token is valid (already validated by finding the session above)

    # Step 3: Find the student and verify device binding
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return jsonify({'error': 'Student not enrolled. Please enroll first.'}), 404

    if student.device_uuid != device_uuid:
        return jsonify({
            'error': 'Device mismatch. This device is not registered to your account.'
        }), 403

    if not student.is_active:
        return jsonify({'error': 'Student account is deactivated'}), 403

    # Step 4: Check for duplicate submission
    existing = Attendance.query.filter_by(
        student_id=student.id,
        session_id=session.id
    ).first()

    if existing:
        return jsonify({
            'error': 'Already checked in for this session',
            'attendance': existing.to_dict()
        }), 409

    # All checks passed — determine status (present vs late)
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

    # Queue for cloud sync
    sync_entry = SyncQueue(table_name='attendance', record_id=attendance.id)
    db.session.add(sync_entry)
    db.session.commit()

    return jsonify({
        'message': f'Attendance recorded as {status}',
        'attendance': attendance.to_dict()
    }), 201


@attendance_bp.route('/api/attendance/<int:session_id>', methods=['GET'])
def get_session_attendance(session_id):
    """Get all attendance records for a specific session."""
    session = Session.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    records = Attendance.query.filter_by(session_id=session_id).all()

    return jsonify({
        'session': session.to_dict(),
        'attendance': [r.to_dict() for r in records],
        'total_present': sum(1 for r in records if r.status == 'present'),
        'total_late': sum(1 for r in records if r.status == 'late'),
        'total_flagged': sum(1 for r in records if r.status == 'flagged'),
    }), 200


@attendance_bp.route('/api/attendance/override', methods=['POST'])
def manual_override():
    """
    Lecturer manually marks a student present or absent.
    
    Expects JSON:
    {
        "student_id": "CSC/2023/001",
        "session_id": 1,
        "status": "present"  (present / late / flagged / absent)
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    student_matric = data.get('student_id', '').strip()
    session_id = data.get('session_id')
    status = data.get('status', 'present').strip()

    if not student_matric or not session_id:
        return jsonify({'error': 'student_id and session_id are required'}), 400

    if status not in ('present', 'late', 'flagged', 'absent'):
        return jsonify({'error': 'Invalid status. Must be: present, late, flagged, or absent'}), 400

    student = Student.query.filter_by(student_id=student_matric).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    session = Session.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Check if record exists
    existing = Attendance.query.filter_by(
        student_id=student.id,
        session_id=session_id
    ).first()

    if status == 'absent' and existing:
        # Remove the attendance record
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'message': 'Attendance record removed (marked absent)'}), 200

    if existing:
        # Update existing record
        existing.status = status
        db.session.commit()
        return jsonify({
            'message': f'Attendance updated to {status}',
            'attendance': existing.to_dict()
        }), 200
    else:
        # Create new record (manual entry)
        attendance = Attendance(
            student_id=student.id,
            session_id=session_id,
            status=status
        )
        db.session.add(attendance)
        db.session.commit()

        # Queue for cloud sync
        sync_entry = SyncQueue(table_name='attendance', record_id=attendance.id)
        db.session.add(sync_entry)
        db.session.commit()

        return jsonify({
            'message': f'Attendance manually recorded as {status}',
            'attendance': attendance.to_dict()
        }), 201
