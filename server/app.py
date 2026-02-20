"""
Offline LAN-Based Attendance System — Main Server Application

This is the entry point for the Flask + Socket.IO server.
Run with: python app.py
"""
import sys
import os

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from config import Config
from database import init_db

# Initialize Flask app
app = Flask(__name__, static_folder=None)
app.config.from_object(Config)

# Enable CORS for LAN access
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize database
init_db(app)

# Register route blueprints
from routes.enrollment import enrollment_bp
from routes.sessions import sessions_bp
from routes.attendance import attendance_bp
from routes.lecturer import lecturer_bp

app.register_blueprint(enrollment_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(lecturer_bp)

# Register WebSocket events
from sockets.events import register_socket_events
register_socket_events(socketio)

# ─── Serve the PWA client ───────────────────────────────

CLIENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'client')


@app.route('/')
def serve_student_page():
    """Serve the student PWA client."""
    return send_from_directory(CLIENT_DIR, 'index.html')


@app.route('/lecturer')
def serve_lecturer_page():
    """Serve the lecturer dashboard."""
    return send_from_directory(CLIENT_DIR, 'lecturer.html')


@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(CLIENT_DIR, 'css'), filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(CLIENT_DIR, 'js'), filename)


@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(CLIENT_DIR, 'manifest.json')


@app.route('/sw.js')
def serve_sw():
    return send_from_directory(CLIENT_DIR, 'sw.js')


# ─── Health check ───────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return {'status': 'ok', 'service': 'offline-attendance-server'}, 200


# ─── Run ────────────────────────────────────────────────

if __name__ == '__main__':
    import socket

    # Get the LAN IP address for display
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = '127.0.0.1'

    port = 5000

    print("=" * 60)
    print("  Offline LAN-Based Attendance System")
    print("=" * 60)
    print(f"  Student client:   http://{local_ip}:{port}/")
    print(f"  Lecturer panel:   http://{local_ip}:{port}/lecturer")
    print(f"  Health check:     http://{local_ip}:{port}/api/health")
    print("=" * 60)
    print(f"  Local network:    Share the IP above with students")
    print("=" * 60)

    socketio.run(app, host='0.0.0.0', port=port, debug=True)
