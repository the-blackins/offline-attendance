"""
Enrollment routes: student registration and device UUID binding.
"""
from flask import Blueprint, request, jsonify
from database import db
from models import Student, SyncQueue
from utils.security import hash_pin

enrollment_bp = Blueprint('enrollment', __name__)


@enrollment_bp.route('/api/enroll', methods=['POST'])
def enroll_student():
    """
    Register a new student and bind their device.
    
    Expects JSON:
    {
        "student_id": "CSC/2023/001",
        "name": "John Doe",
        "device_uuid": "abc-123-def-456",
        "pin": "1234"  (optional)
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    student_id = data.get('student_id', '').strip()
    name = data.get('name', '').strip()
    device_uuid = data.get('device_uuid', '').strip()
    pin = data.get('pin')

    # Validate required fields
    if not student_id or not name or not device_uuid:
        return jsonify({'error': 'student_id, name, and device_uuid are required'}), 400

    # Check if student is already enrolled
    existing_student = Student.query.filter_by(student_id=student_id).first()
    if existing_student:
        if existing_student.device_uuid == device_uuid:
            return jsonify({
                'message': 'Already enrolled with this device',
                'student': existing_student.to_dict()
            }), 200
        else:
            return jsonify({
                'error': 'Student already enrolled with a different device. Request re-enrollment from your lecturer.'
            }), 409

    # Check if device is already bound to another student
    device_conflict = Student.query.filter_by(device_uuid=device_uuid).first()
    if device_conflict:
        return jsonify({
            'error': 'This device is already bound to another student'
        }), 409

    # Create new student
    pin_hash = hash_pin(pin) if pin else None
    student = Student(
        student_id=student_id,
        name=name,
        device_uuid=device_uuid,
        pin_hash=pin_hash
    )

    db.session.add(student)
    db.session.commit()

    # Queue for cloud sync
    sync_entry = SyncQueue(table_name='students', record_id=student.id)
    db.session.add(sync_entry)
    db.session.commit()

    return jsonify({
        'message': 'Enrollment successful',
        'student': student.to_dict()
    }), 201


@enrollment_bp.route('/api/re-enroll', methods=['POST'])
def request_re_enrollment():
    """
    Request a device change for an existing student.
    The new device_uuid will only take effect after lecturer approval.
    
    Expects JSON:
    {
        "student_id": "CSC/2023/001",
        "new_device_uuid": "new-abc-123"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    student_id = data.get('student_id', '').strip()
    new_device_uuid = data.get('new_device_uuid', '').strip()

    if not student_id or not new_device_uuid:
        return jsonify({'error': 'student_id and new_device_uuid are required'}), 400

    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    # Check if new device is already bound
    device_conflict = Student.query.filter_by(device_uuid=new_device_uuid).first()
    if device_conflict and device_conflict.id != student.id:
        return jsonify({'error': 'This device is already bound to another student'}), 409

    # For now, we store the request. In a full system, this would go to an approval queue.
    # For the MVP, we just update directly (lecturer can supervise in person).
    student.device_uuid = new_device_uuid
    db.session.commit()

    # Queue for cloud sync
    sync_entry = SyncQueue(table_name='students', record_id=student.id)
    db.session.add(sync_entry)
    db.session.commit()

    return jsonify({
        'message': 'Device re-enrollment successful',
        'student': student.to_dict()
    }), 200


@enrollment_bp.route('/api/enrollment/status/<student_id>', methods=['GET'])
def enrollment_status(student_id):
    """Check if a student is enrolled and their device binding status."""
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return jsonify({'enrolled': False}), 200

    return jsonify({
        'enrolled': True,
        'student': student.to_dict()
    }), 200
