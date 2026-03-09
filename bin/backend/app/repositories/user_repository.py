from bson.objectid import ObjectId


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

    def find_by_id(self, user_id: str):
        return self.mongo.db["users"].find_one({"_id": ObjectId(user_id)})

    def create_user(self, user_data: dict):
        return self.mongo.db["users"].insert_one(user_data)

    def update_by_username(self, username: str, update_fields: dict):
        return self.mongo.db["users"].update_one(
            {"username": username},
            {"$set": update_fields}
        )

    def update_by_id(self, user_id: str, update_fields: dict):
        return self.mongo.db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )

    def delete_by_username(self, username: str):
        return self.mongo.db["users"].delete_one({"username": username})

    def username_exists(self, username: str):
        return self.mongo.db["users"].find_one({"username": username}) is not None

    def email_exists(self, email: str):
        return self.mongo.db["users"].find_one({"email": email}) is not None

    def create_indexes(self):
        self.mongo.db["users"].create_index("username", unique=True)
        self.mongo.db["users"].create_index("email", unique=True)