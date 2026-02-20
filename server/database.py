"""
Database initialization and helpers.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize the database with the Flask app and create all tables."""
    db.init_app(app)
    with app.app_context():
        # Enable WAL mode for crash resilience
        from sqlalchemy import event

        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        # Import models so they're registered
        import models  # noqa: F401
        db.create_all()
        print("[DB] Database initialized with WAL mode")
