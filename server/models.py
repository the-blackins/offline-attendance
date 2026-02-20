"""
SQLAlchemy models for the Offline Attendance System.

Local database tables:
- Student: enrolled students with device binding
- Session: attendance sessions (controlled by Arduino/lecturer)
- Attendance: individual check-in records
- SyncQueue: tracks records pending cloud sync
"""
from datetime import datetime
from database import db


class Student(db.Model):
    """A student enrolled in the system with a bound device."""
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)  # matric number
    name = db.Column(db.String(150), nullable=False)
    device_uuid = db.Column(db.String(100), unique=True, nullable=True)
    pin_hash = db.Column(db.String(256), nullable=True)  # optional PIN
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    attendances = db.relationship('Attendance', backref='student', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'device_uuid': self.device_uuid,
            'enrolled_at': self.enrolled_at.isoformat() if self.enrolled_at else None,
            'is_active': self.is_active
        }


class Session(db.Model):
    """An attendance session, typically one per class period."""
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)
    session_token = db.Column(db.String(100), unique=True, nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    attendances = db.relationship('Attendance', backref='session', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'course_code': self.course_code,
            'session_token': self.session_token,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'is_active': self.is_active,
            'attendance_count': len(self.attendances)
        }


class Attendance(db.Model):
    """A single attendance check-in record."""
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='present')  # present / late / flagged

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_matric': self.student.student_id if self.student else None,
            'student_name': self.student.name if self.student else None,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status
        }


class SyncQueue(db.Model):
    """Tracks records that need to be synced to the cloud."""
    __tablename__ = 'sync_queue'

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending / synced / failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    synced_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'table_name': self.table_name,
            'record_id': self.record_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None
        }
