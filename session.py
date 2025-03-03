from contextlib import contextmanager
from flask import current_app
from extensions import db

@contextmanager
def session_scope():
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Session error: {str(e)}")
        raise
    finally:
        db.session.close()

class SessionManager:

    def __init__(self):
        self.sessions = {}

    def get_session(self, key):
        return self.sessions.get(key)

    def set_session(self, key, value):
        self.sessions[key] = value

session_manager = SessionManager()