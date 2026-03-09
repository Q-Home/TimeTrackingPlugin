class UserRepository:
    def __init__(self, mongo):
        self.mongo = mongo

    def find_by_username(self, username: str):
        return self.mongo.db["users"].find_one({"username": username})

    def find_by_email(self, email: str):
        return self.mongo.db["users"].find_one({"email": email})

    def find_by_username_or_email(self, value: str):
        return self.mongo.db["users"].find_one({
            "$or": [
                {"username": value},
                {"email": value}
            ]
        })

    def create_user(self, user_data: dict):
        return self.mongo.db["users"].insert_one(user_data)

    def create_indexes(self):
        self.mongo.db["users"].create_index("username", unique=True)
        self.mongo.db["users"].create_index("email", unique=True)