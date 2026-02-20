"""Quick test script for Phase 1 API endpoints."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Avoid eventlet monkey patching for testing
os.environ['TESTING'] = '1'

from flask import Flask
from flask_cors import CORS
from config import Config
from database import db, init_db

# Create a test app directly (without SocketIO/eventlet)
app = Flask(__name__)
app.config.from_object(Config)
app.config['TESTING'] = True
CORS(app)

init_db(app)

from routes.enrollment import enrollment_bp
from routes.sessions import sessions_bp
from routes.attendance import attendance_bp
from routes.lecturer import lecturer_bp

app.register_blueprint(enrollment_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(lecturer_bp)

@app.route('/api/health')
def health():
    return {'status': 'ok'}, 200

client = app.test_client()

# Run tests
print("Running Phase 1 API tests...")
print("-" * 40)

# 1. Health
r = client.get('/api/health')
print(f"1. Health: {r.status_code} {'PASS' if r.status_code == 200 else 'FAIL'}")

# 2. Enroll
r = client.post('/api/enroll', json={
    'student_id': 'CSC/2023/001', 'name': 'John Doe', 'device_uuid': 'test-001'
})
data = r.get_json()
print(f"2. Enroll: {r.status_code} {data.get('message', data.get('error'))}")
assert r.status_code == 201, f"Expected 201, got {r.status_code}"

# 3. Duplicate enroll (same device = OK)
r = client.post('/api/enroll', json={
    'student_id': 'CSC/2023/001', 'name': 'John Doe', 'device_uuid': 'test-001'
})
data = r.get_json()
print(f"3. Dup enroll (same device): {r.status_code} {data.get('message', data.get('error'))}")
assert r.status_code == 200

# 4. Start session
r = client.post('/api/session/start', json={'course_code': 'CSC301'})
data = r.get_json()
print(f"4. Start session: {r.status_code} {data.get('message', data.get('error'))}")
assert r.status_code == 201
token = data['session']['session_token']

# 5. Check-in
r = client.post('/api/check-in', json={
    'student_id': 'CSC/2023/001', 'device_uuid': 'test-001', 'session_token': token
})
data = r.get_json()
print(f"5. Check-in: {r.status_code} {data.get('message', data.get('error'))}")
assert r.status_code == 201

# 6. Duplicate check-in
r = client.post('/api/check-in', json={
    'student_id': 'CSC/2023/001', 'device_uuid': 'test-001', 'session_token': token
})
data = r.get_json()
print(f"6. Duplicate: {r.status_code} {data.get('error', 'no error')}")
assert r.status_code == 409

# 7. Wrong device
r = client.post('/api/check-in', json={
    'student_id': 'CSC/2023/001', 'device_uuid': 'wrong-device', 'session_token': token
})
data = r.get_json()
print(f"7. Wrong device: {r.status_code} {data.get('error', 'no error')}")
assert r.status_code == 403

# 8. Get attendance
r = client.get('/api/attendance/1')
data = r.get_json()
print(f"8. Attendance: {r.status_code} records={len(data.get('attendance', []))}")
assert r.status_code == 200
assert len(data['attendance']) == 1

# 9. End session
r = client.post('/api/session/end', json={'course_code': 'CSC301'})
data = r.get_json()
print(f"9. End session: {r.status_code} {data.get('message', data.get('error'))}")
assert r.status_code == 200

# 10. Check-in after session ended
r = client.post('/api/check-in', json={
    'student_id': 'CSC/2023/001', 'device_uuid': 'test-001', 'session_token': token
})
data = r.get_json()
print(f"10. After end: {r.status_code} {data.get('error', 'no error')}")
assert r.status_code == 403

# 11. List students
r = client.get('/api/students')
data = r.get_json()
print(f"11. Students: {r.status_code} total={data.get('total', 0)}")
assert r.status_code == 200

# 12. Active session (none)
r = client.get('/api/session/active')
data = r.get_json()
print(f"12. No active session: {r.status_code} active={data.get('active')}")
assert data['active'] == False

print("-" * 40)
print("=== ALL 12 TESTS PASSED ===")
