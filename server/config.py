"""
Configuration for the Offline Attendance System server.
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'offline-attendance-dev-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'attendance.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session settings
    SESSION_TOKEN_LENGTH = 32
    QR_REFRESH_INTERVAL = 30  # seconds

    # Serial bridge settings (Arduino)
    SERIAL_PORT = os.environ.get('SERIAL_PORT', 'COM3')  # Windows default; Linux: /dev/ttyACM0
    SERIAL_BAUD_RATE = 9600

    # Cloud sync settings (Supabase)
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
    SYNC_CHECK_INTERVAL = 60  # seconds

    # HMAC secret for signed payloads
    HMAC_SECRET = os.environ.get('HMAC_SECRET', 'hmac-dev-secret-change-in-production')

    # Late threshold (minutes after session start)
    LATE_THRESHOLD_MINUTES = 15
