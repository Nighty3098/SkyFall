from __future__ import annotations

import random


class CollectorState:
    def __init__(self):
        self.request_counter = 0
        self.proxies: list[tuple] = []
        self.current_proxy: tuple | None = None
        self.use_proxy = False
        self.multi_acc_sessions: list[str] = []
        self.current_session_index = 0
        self.switch_request_threshold = 100
        self.request_since_switch = 0

    def reset(self):
        self.request_counter = 0
        self.proxies.clear()
        self.current_proxy = None
        self.use_proxy = False
        self.multi_acc_sessions.clear()
        self.current_session_index = 0
        self.switch_request_threshold = 100
        self.request_since_switch = 0

    def rotate_proxy(self) -> tuple | None:
        if self.current_proxy and self.proxies:
            try:
                self.proxies.remove(self.current_proxy)
            except ValueError:
                pass
            self.current_proxy = None
        if self.proxies:
            self.current_proxy = random.choice(self.proxies)
        return self.current_proxy

    def remove_current_proxy(self):
        if self.current_proxy and self.proxies:
            try:
                self.proxies.remove(self.current_proxy)
            except ValueError:
                pass
            self.current_proxy = None
