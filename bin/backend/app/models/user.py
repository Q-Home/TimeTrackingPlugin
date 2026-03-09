from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role
        self.authenticated = True

    def get_id(self):
        return self.username