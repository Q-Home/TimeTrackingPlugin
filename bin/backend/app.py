import os
import dotenv
import logging
from flask import Flask, request, jsonify, redirect, url_for, session, render_template
from flask_session import Session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson.objectid import ObjectId
import bcrypt

from datetime import timedelta
import datetime
from werkzeug.utils import secure_filename
import threading
from urllib.parse import unquote

print(bcrypt.__file__)
print(bcrypt.__version__)
# Load environment variables
dotenv.load_dotenv()

# Setup logging
# logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Secret key for sessions
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')

# Initialize MongoDB client
# MongoDB Configuration
# app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)
if not mongo:
    print("Error connecting to MongoDB")
else:
    print("Connected to MongoDB")



# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_html"  # Replace with the actual login route

# Configure server-side session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
# Base API endpoint
endpoint = '/api/v1'
# Een dictionary om de laatste heartbeat tijd van elke robot bij te houden
last_heartbeat_times = {}
threads = {}
# Functie om de status van de robot bij te werken in de database



def log_error(message):
    try:
        mongo.cx['Logs']['logs'].insert_one({
            "message": message,
            "type": "Error",
            "timestamp": datetime.datetime.utcnow()
        })
    except Exception as e:
        print(f"Failed to log error: {e}")

# Function to log warnings to the database


def log_warning(message):
    try:
        mongo.cx['Logs']['logs'].insert_one({
            "message": message,
            "type": "Warning",
            "timestamp": datetime.datetime.utcnow()
        })
    except Exception as e:
        print(f"Failed to log warning: {e}")

# Function to log info messages to the database


def log_info(message):
    try:
        mongo.cx['Logs']['logs'].insert_one({
            "message": message,
            "type": "Info",
            "timestamp": datetime.datetime.utcnow()
        })
    except Exception as e:
        print(f"Failed to log info: {e}")



class User(UserMixin):
    def __init__(self, username, role):
        self.username = username
        self.role = role
        self.authenticated = False  # Initialize authenticated to False

    def is_active(self):
        return True

    def get_id(self):
        return self.username

    def is_authenticated(self):
        return self.authenticated

    def is_anonymous(self):
        return False


# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    try:
        user = mongo.cx['User']['users'].find_one({"username": user_id})
        if user:
            user_obj = User(user["username"], user['role'])
            user_obj.authenticated = True
            return user_obj
    except Exception as e:
        log_error(f"Error loading user: {e}")
    return None


@app.route(f'{endpoint}/is_logged_in/', methods=['GET'])
def is_logged_in():
    """
    Checks if the user is logged in.
    """
    try:
        if current_user.is_authenticated:
            return jsonify({
                "message": "User is logged in.",
                "username": current_user.id,
                "role": current_user.role
            }), 200
        else:
            return jsonify({"message": "User is not logged in."}), 401
    except Exception as e:
        log_error(f"Error checking login status: {e}")
        return jsonify({"message": "An error occurred while checking login status."}), 500


@app.route(f'{endpoint}/login/', methods=["POST"])
def login_html():
    """
    Processes login attempts based on username or email.
    """
    try:
        print("Login attempt")
        data = request.get_json()
        username_or_email = data.get('username')
        password = data.get('password')

        if not username_or_email or not password:
            return jsonify({"message": "Username and password are required."}), 400

        user = mongo.cx['User']['users'].find_one({
            "$or": [
                {"username": username_or_email},
                {"email": username_or_email}
            ]
        })

        if user and bcrypt.checkpw(password.encode("utf-8"), user['password'].encode("utf-8")):
            if user["blocked"]:
                return jsonify({"message": "Account is blocked."}), 403
            log_info(f"User successfully logged in: {user['username']}")
            return jsonify({"username": user["username"], "role": user["role"]}), 200
        else:
            return jsonify({"message": "Invalid login credentials."}), 401
    except Exception as e:
        log_error(f"Error during login: {e}")
        return jsonify({"message": "An error occurred during login."}), 500


@app.route(f'{endpoint}/users/', methods=['GET'])
def get_users():
    """
    Retrieve all users from the Users collection.
    Endpoint: /api/v1/users/
    Returns:
        - 200 with a list of users
    """
    try:
        users = mongo.cx['User']['users'].find()
        user_list = [{
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'company_name': user['company_name'],
            'user_role': user['role'],
            'username': user['username'],
            'email': user['email'],
            "blocked": user['blocked']
        } for user in users]
        return jsonify(users=user_list), 200
    except Exception as e:
        log_error(f"Error retrieving users: {e}")
        return jsonify({'error': str(e)}), 500


@app.route(f'{endpoint}/users/<username>/', methods=['GET'])
def get_user(username):

    user = mongo.cx['User']['users'].find_one({"username": username})
    # print (user)
    user1 = {
        'user_id': str(user['_id']),
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'company_name': user['company_name'],
        'user_role': user['role'],
        'username': user['username'],
        'email': user['email'],
        "blocked": user['blocked']
    }
    return jsonify(user1), 200


@app.route(f'{endpoint}/logout/', methods=["POST"])
def logout():
    """
    Logs out the current user.
    """
    logout_user()
    log_info("User logged out")
    return jsonify({"message": "Logged out successfully."}), 200


@app.route(f'{endpoint}/users/<user_id>/block', methods=["PUT"])
def block_user(user_id):
    try:
        # Controleer of de gebruikersnaam al bestaat
        updated_fields = {"blocked": True}
        if mongo.cx['User']['users'].find_one({"username": user_id}):
            result = mongo.cx['User']['users'].update_one(
                {"username": user_id}, {'$set': updated_fields})
            if result.matched_count == 0:
                log_error(f"User not found: {user_id}")
                return jsonify({"message": "User not found."}), 404
            else:
                log_info(f"User Blocked: {user_id}")
                return jsonify({"message": "User updated successfully."}), 200
        else:
            log_error(f"User not found: {user_id}")
            return jsonify({"message": "User not found."}), 404
    except Exception as e:
        log_error(f"Error updating user: {e}")
        return jsonify({"message": "An error occurred while updating the user."}), 500


@app.route(f'{endpoint}/users/<user_id>/unblock', methods=["PUT"])
def unblock_user(user_id):
    try:
        # Controleer of de gebruikersnaam al bestaat
        updated_fields = {"blocked": False}
        if mongo.cx['User']['users'].find_one({"username": user_id}):
            result = mongo.cx['User']['users'].update_one(
                {"username": user_id}, {'$set': updated_fields})
            if result.matched_count == 0:
                log_error(f"User not found: {user_id}")
                return jsonify({"message": "User not found."}), 404
            else:
                log_info(f"User unblock: {user_id}")
                return jsonify({"message": "User updated successfully."}), 200
        else:
            log_error(f"User not found: {user_id}")
            return jsonify({"message": "User not found."}), 404
    except Exception as e:
        log_error(f"Error updating user: {e}")
        return jsonify({"message": "An error occurred while updating the user."}), 500


@app.route(f'{endpoint}/users/<user_id>', methods=["PUT"])
def update_user(user_id):
    """
    Update an existing user (only for admins).
    """
    try:
        data = request.get_json()
        update_fields = {}

        if "username" in data:
            update_fields["username"] = data["username"]
        if "first_name" in data:
            update_fields["first_name"] = data["first_name"]
        if "last_name" in data:
            update_fields["last_name"] = data["last_name"]
        if "email" in data:
            update_fields["email"] = data["email"]
        if "company_name" in data:
            update_fields["company_name"] = data["company_name"]
        if "password" in data:
            update_fields["password"] = bcrypt.hashpw(
                data["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        if "user_role" in data:
            update_fields["role"] = data["user_role"]
        if "blocked" in data:
            update_fields["blocked"] = data["blocked"]

        # Log user update attempt
        # print(f"Updating user: {user_id}")

        if not update_fields:
            log_error("No fields to update")
            return jsonify({"message": "No fields to update."}), 400

        result = mongo.cx['User']['users'].update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_fields})

        if result.matched_count == 0:
            log_error(f"User not found: {user_id}")
            return jsonify({"message": "User not found."}), 404

        log_info(f"User updated: {user_id}")
        return jsonify({"message": "User updated successfully."}), 200
    except Exception as e:
        log_error(f"Error updating user: {e}")
        return jsonify({"message": "An error occurred while updating the user."}), 500


@app.route(f'{endpoint}/users/', methods=["POST"])
def create_user():
    """
    Creëert een nieuwe gebruiker (alleen voor admins).
    """
    try:
        data = request.get_json()
        username = data.get("username")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        company_name = data.get("company_name")
        password = data.get("password")
        role = data.get("user_role")
        blocked = data.get("blocked", False)

        # Log user creation attempt
        print(f"Creating user: {username}, Role: {role}")

        if not username or not password or not email:
            log_error(f"Missing fields: {username}, {email}, {password}")
            return jsonify({"message": "Username, password, and email are required."}), 400

        # Controleer of de gebruikersnaam al bestaat
        if mongo.cx['User']['users'].find_one({"username": username}):
            log_error(f"Username already exists: {username}")
            return jsonify({"message": "Username already exists. Please choose another."}), 400

        # Controleer of het e-mailadres al bestaat
        if mongo.cx['User']['users'].find_one({"email": email}):
            log_error(f"Email already exists: {email}")
            return jsonify({"message": "Email address already exists. Please choose another."}), 400

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        mongo.cx['User']['users'].insert_one({
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "company_name": company_name,
            "password": hashed_pw.decode("utf-8"),
            "role": role,
            "blocked": blocked
        })
        log_info(f"User created: {username}")
        return jsonify({"message": "User created successfully."}), 201
    except Exception as e:
        log_error(f"Error creating user: {e}")
        return jsonify({"message": "An error occurred while creating the user."}), 500


@app.route(f'{endpoint}/users/<username>/', methods=["DELETE"])
def delete_user(username):
    """
    Deletes a user by username (admin only).
    """
    result = mongo.cx['User']['users'].delete_one({"username": username})
    if result.deleted_count == 1:
        log_info(f"User deleted: {username}")
        return jsonify({"message": f"User {username} deleted successfully."}), 200
    else:
        log_error(f"User not found: {username}")
        return jsonify({"message": "User not found."}), 404


@app.route('/api/v1/logs/', methods=['GET'])
def get_logs():
    try:
        # Haal alle logs op uit de database
        logs_cursor = mongo.cx['Logs']['logs'].find().sort(
            "timestamp", -1)  # Sorteer op timestamp aflopend
        print(logs_cursor)
        logs = []
        for log in logs_cursor:
            logs.append({
                "message": log.get("message"),
                "type": log.get("type"),
                # Format datum
                "date": log.get("timestamp").strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify({"logs": logs}), 200
    except Exception as e:
        log_error(f"Error retrieving logs: {e}")
        return jsonify({"error": str(e)}), 500
    
def create_default_admin():
    """
    Create default admin user if it doesn't exist
    """
    try:
        if not mongo.cx['User']['users'].find_one({"username": "admin"}):
            hashed_pw = bcrypt.hashpw("admin".encode("utf-8"), bcrypt.gensalt())
            mongo.cx['User']['users'].insert_one({
                "username": "admin",
                "first_name": "Administrator", 
                "last_name": "User",
                "email": "admin@timetracking.local",
                "company_name": "TimeTracking System",
                "password": hashed_pw.decode("utf-8"),
                "role": "admin",
                "blocked": False
            })
            log_info("Default admin user created")
            print("Default admin user created: username=admin, password=admin")
    except Exception as e:
        log_error(f"Error creating default admin: {e}")

if __name__ == '__main__':
    try:
        log_info("Starting Flask app...")
        app.run(host='0.0.0.0', port=5000, debug=True)
        create_default_admin()  # Create admin user on startup
    except Exception as e:
        log_error(f"Error starting Flask app: {e}")
    except KeyboardInterrupt:
        log_info("Shutting down Flask app...")
