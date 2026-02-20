"""
Session routes: start/stop attendance sessions, QR code generation.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from database import db
from models import Session
from utils.security import generate_session_token
from utils.qr import generate_qr_base64

sessions_bp = Blueprint('sessions', __name__)


@sessions_bp.route('/api/session/start', methods=['POST'])
def start_session():
    """
    Start a new attendance session.
    
    Expects JSON:
    {
        "course_code": "CSC301"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    course_code = data.get('course_code', '').strip()
    if not course_code:
        return jsonify({'error': 'course_code is required'}), 400

    # Check if there's already an active session for this course
    active_session = Session.query.filter_by(
        course_code=course_code, is_active=True
    ).first()

    if active_session:
        return jsonify({
            'error': 'An active session already exists for this course',
            'session': active_session.to_dict()
        }), 409

    # Create new session
    token = generate_session_token()
    session = Session(
        course_code=course_code,
        session_token=token,
        is_active=True
    )

    db.session.add(session)
    db.session.commit()

    return jsonify({
        'message': 'Session started',
        'session': session.to_dict()
    }), 201


@sessions_bp.route('/api/session/end', methods=['POST'])
def end_session():
    """
    End an active attendance session.
    
    Expects JSON:
    {
        "session_id": 1
    }
    OR:
    {
        "course_code": "CSC301"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    session_id = data.get('session_id')
    course_code = data.get('course_code', '').strip()

    if session_id:
        session = Session.query.get(session_id)
    elif course_code:
        session = Session.query.filter_by(
            course_code=course_code, is_active=True
        ).first()
    else:
        return jsonify({'error': 'session_id or course_code is required'}), 400

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    if not session.is_active:
        return jsonify({'error': 'Session is already ended'}), 400

    session.is_active = False
    session.end_time = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': 'Session ended',
        'session': session.to_dict()
    }), 200


@sessions_bp.route('/api/session/active', methods=['GET'])
def get_active_session():
    """Get the currently active session, optionally filtered by course code."""
    course_code = request.args.get('course_code', '').strip()

    if course_code:
        session = Session.query.filter_by(
            course_code=course_code, is_active=True
        ).first()
    else:
        session = Session.query.filter_by(is_active=True).first()

    if not session:
        return jsonify({'active': False, 'session': None}), 200

    return jsonify({
        'active': True,
        'session': session.to_dict()
    }), 200


@sessions_bp.route('/api/session/qr', methods=['GET'])
def get_session_qr():
    """Generate a QR code for the active session's token."""
    course_code = request.args.get('course_code', '').strip()

    if course_code:
        session = Session.query.filter_by(
            course_code=course_code, is_active=True
        ).first()
    else:
        session = Session.query.filter_by(is_active=True).first()

    if not session:
        return jsonify({'error': 'No active session'}), 404

    qr_data = f"{session.session_token}"
    qr_image = generate_qr_base64(qr_data)

    return jsonify({
        'session_token': session.session_token,
        'course_code': session.course_code,
        'qr_code': qr_image
    }), 200


@sessions_bp.route('/api/sessions/history', methods=['GET'])
def session_history():
    """Get session history, optionally filtered by course code."""
    course_code = request.args.get('course_code', '').strip()
    limit = request.args.get('limit', 20, type=int)

    query = Session.query.order_by(Session.start_time.desc())
    if course_code:
        query = query.filter_by(course_code=course_code)

    sessions = query.limit(limit).all()
    return jsonify({
        'sessions': [s.to_dict() for s in sessions]
    }), 200
