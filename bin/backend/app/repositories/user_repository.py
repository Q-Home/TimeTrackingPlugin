from bson.objectid import ObjectId


class UserRepository:
    def __init__(self, mongo):
        self.mongo = mongo

    def find_by_username(self, username: str):
        return self.mongo.db["users"].find_one({"username": username})

    def find_by_email(self, email: str):
        return self.mongo.db["users"].find_one({"email": email})

    def find_by_badge_code(self, badge_code: str):
        return self.mongo.db["users"].find_one({"badge_code": badge_code})

    def find_by_username_or_email(self, value: str):
        return self.mongo.db["users"].find_one({
            "$or": [
                {"username": value},
                {"email": value}
            ]
        })

    def find_by_id(self, user_id: str):
        return self.mongo.db["users"].find_one({"_id": ObjectId(user_id)})

    def find_all(self):
        return list(self.mongo.db["users"].find({}, {"password": 0}).sort("username", 1))

    def create_user(self, user_data: dict):
        return self.mongo.db["users"].insert_one(user_data)

    def update_by_username(self, username: str, update_fields: dict):
        return self.mongo.db["users"].update_one(
            {"username": username},
            {"$set": update_fields}
        )

    def update_by_id(self, user_id: str, update_fields: dict, unset_fields: dict = None):
        update_ops = {"$set": update_fields}
        if unset_fields:
            update_ops["$unset"] = unset_fields

        return self.mongo.db["users"].update_one(
            {"_id": ObjectId(user_id)},
            update_ops
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
        
    def create_default_admin_if_missing(self, user_data: dict):
        return self.mongo.db["users"].update_one(
            {
                "$or": [
                    {"username": user_data["username"]},
                    {"email": user_data["email"]}
                ]
            },
            {"$setOnInsert": user_data},
            upsert=True
        )
