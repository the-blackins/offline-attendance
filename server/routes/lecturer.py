"""
Lecturer routes: authentication, course management, student listing.
"""
from flask import Blueprint, request, jsonify, session
from database import db
from models import Student

lecturer_bp = Blueprint('lecturer', __name__)

# For the MVP, we use a simple password stored in config.
# In production, this would use proper user accounts in the cloud DB.


@lecturer_bp.route('/api/lecturer/login', methods=['POST'])
def lecturer_login():
    """
    Simple lecturer authentication for MVP.
    
    Expects JSON:
    {
        "password": "admin123"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    password = data.get('password', '')

    # MVP: simple password check. Production: Supabase auth.
    if password == 'admin123':
        session['is_lecturer'] = True
        return jsonify({'message': 'Login successful', 'authenticated': True}), 200
    else:
        return jsonify({'error': 'Invalid password'}), 401


@lecturer_bp.route('/api/lecturer/logout', methods=['POST'])
def lecturer_logout():
    """Log out the lecturer."""
    session.pop('is_lecturer', None)
    return jsonify({'message': 'Logged out'}), 200


@lecturer_bp.route('/api/students', methods=['GET'])
def list_students():
    """Get all enrolled students."""
    students = Student.query.order_by(Student.student_id).all()
    return jsonify({
        'students': [s.to_dict() for s in students],
        'total': len(students)
    }), 200


@lecturer_bp.route('/api/students/<student_id>', methods=['GET'])
def get_student(student_id):
    """Get a specific student by matric number."""
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    return jsonify({'student': student.to_dict()}), 200


@lecturer_bp.route('/api/students/<student_id>/attendance', methods=['GET'])
def student_attendance_history(student_id):
    """Get attendance history for a specific student."""
    from models import Attendance, Session as AttSession

    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    records = Attendance.query.filter_by(student_id=student.id)\
        .order_by(Attendance.timestamp.desc()).all()

    return jsonify({
        'student': student.to_dict(),
        'attendance': [r.to_dict() for r in records],
        'total_sessions_attended': len(records),
        'present_count': sum(1 for r in records if r.status == 'present'),
        'late_count': sum(1 for r in records if r.status == 'late'),
    }), 200
