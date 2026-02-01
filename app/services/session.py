import json
import os
from typing import Optional, Dict
from app.config import SESSION_FILE

class SessionManager:
    def __init__(self, file_path: str = SESSION_FILE):
        self.file_path = file_path
        self.sessions: Dict[str, str] = self._load_sessions()

    def _load_sessions(self) -> Dict[str, str]:
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_sessions(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error guardando sesiones: {e}")

    def get_session(self, phone: str) -> Optional[str]:
        return self.sessions.get(phone)

    def set_session(self, phone: str, state: Optional[str]):
        if state is None:
            if phone in self.sessions:
                del self.sessions[phone]
        else:
            self.sessions[phone] = state
        self._save_sessions()

# Instancia global (singleton)
session_manager = SessionManager()
