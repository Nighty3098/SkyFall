import os
import random


def load_multi_acc_sessions(path: str) -> list:
    sessions = []
    if not os.path.exists(path):
        return sessions
    for filename in os.listdir(path):
        if filename.endswith(".session"):
            session_path = os.path.join(path, filename)
            sessions.append(session_path)
    return sessions


def get_random_session(sessions: list) -> str | None:
    if not sessions:
        return None
    return random.choice(sessions)
