import os
import logging
from flask import Flask, request, jsonify, redirect, url_for, session, render_template
from flask_session import Session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson.objectid import ObjectId
import bcrypt
from datetime import datetime, timedelta
import re
import threading
from urllib.parse import unquote

print(f"bcrypt location: {bcrypt.__file__}")
print(f"bcrypt version: {bcrypt.__version__}")

# Detecteer Docker omgeving
print("=== ENVIRONMENT DETECTION ===")
in_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV') == 'true'
print(f"Running in Docker: {in_docker}")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
print("✓ Logging configured")

# Initialize Flask app
print("\n=== FLASK SETUP ===")
app = Flask(__name__)
print("✓ Flask app initialized")

CORS(app, resources={r"/*": {"origins": "*"}})
print("✓ CORS configured")

# Secret key for sessions
secret_key = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['SECRET_KEY'] = secret_key
print(f"✓ Secret key set")

# MongoDB Configuration - ZONDER authenticatie
print("\n=== MONGODB SETUP ===")
mongo_uri = os.getenv('MONGO_URI')
print(f"MONGO_URI from environment: {mongo_uri}")

# Verbindingsstrategieën ZONDER authenticatie
if in_docker:
    print("=== DOCKER ENVIRONMENT STRATEGIES (NO AUTH) ===")
    connection_strategies = [
        ("Docker Compose MONGO_URI", mongo_uri),
        ("Docker IP no auth", "mongodb://172.28.0.10:27017/timetracking"),
        ("Docker service name no auth", "mongodb://mongodb:27017/timetracking"),
        ("Docker IP default db", "mongodb://172.28.0.10:27017/"),
        ("Docker service default db", "mongodb://mongodb:27017/"),
    ]
else:
    print("=== LOCAL DEVELOPMENT STRATEGIES (NO AUTH) ===")
    connection_strategies = [
        ("Local MONGO_URI", mongo_uri),
        ("Local no auth", "mongodb://localhost:27017/timetracking"),
        ("Local default db", "mongodb://localhost:27017/"),
        ("Remote no auth", "mongodb://192.168.0.170:27017/timetracking"),
    ]

# Test verbindingen (rest van de code blijft hetzelfde)
mongo = None
successful_uri = None

for strategy_name, uri in connection_strategies:
    if not uri:
        print(f"Skipping {strategy_name} - URI is None")
        continue

    try:
        print(f"\n--- Testing {strategy_name} ---")
        print(f"URI: {uri}")

        app.config["MONGO_URI"] = uri
        test_mongo = PyMongo()
        test_mongo.init_app(app)

        # Test verbinding
        result = test_mongo.db.command('ping')
        print(f"✓ MongoDB ping successful: {result}")

        # Test database naam
        db_name = test_mongo.db.name
        print(f"✓ Connected to database: {db_name}")

        # Test collecties
        try:
            collections = test_mongo.db.list_collection_names()
            print(f"✓ Available collections: {collections}")
        except Exception as coll_e:
            print(f"⚠ Could not list collections: {coll_e}")

        # Test schrijftoegang
        try:
            test_doc = {"test": "connection_test",
                        "timestamp": datetime.utcnow()}
            test_result = test_mongo.db.connection_test.insert_one(test_doc)
            print(f"✓ Write test successful: {test_result.inserted_id}")
            # Cleanup
            test_mongo.db.connection_test.delete_one(
                {"_id": test_result.inserted_id})
            print("✓ Test document cleaned up")
        except Exception as write_e:
            print(f"⚠ Write test failed: {write_e}")

        mongo = test_mongo
        successful_uri = uri
        print(f"✓ SUCCESS: Connected with {strategy_name}")
        break

    except Exception as e:
        print(f"✗ Failed {strategy_name}: {type(e).__name__}: {e}")
        if "Connection refused" in str(e):
            print("  → MongoDB server not running or not accessible")
        elif "authentication" in str(e).lower():
            print("  → Authentication issue (but we're not using auth)")

if successful_uri:
    print(f"\n✓ MongoDB connected: {successful_uri}")
    print(f"✓ Database: {mongo.db.name}")
    print("✓ Authentication: DISABLED")
else:
    print("\n✗ All MongoDB connection attempts failed")
    mongo = None

# Flask-Login setup
print("\n=== FLASK-LOGIN SETUP ===")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
print("✓ Flask-Login configured")

# Configure server-side session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
print("✓ Session configured")

# Base API endpoint
endpoint = '/api/v1'
print(f"✓ API endpoint: {endpoint}")

# Global variables
last_heartbeat_times = {}
threads = {}
print("✓ Global variables initialized")

# Logging functions


def log_error(message):
    print(f"ERROR: {message}")
    try:
        if mongo:
            mongo.db['logs'].insert_one({
                "message": message,
                "type": "Error",
                "timestamp": datetime.utcnow()
            })
    except Exception as e:
        print(f"Failed to log error: {e}")


def log_warning(message):
    print(f"WARNING: {message}")
    try:
        if mongo:
            mongo.db['logs'].insert_one({
                "message": message,
                "type": "Warning",
                "timestamp": datetime.utcnow()
            })
    except Exception as e:
        print(f"Failed to log warning: {e}")


def log_info(message):
    print(f"INFO: {message}")
    try:
        if mongo:
            mongo.db['logs'].insert_one({
                "message": message,
                "type": "Info",
                "timestamp": datetime.utcnow()
            })
    except Exception as e:
        print(f"Failed to log info: {e}")


class User(UserMixin):
    def __init__(self, username, role):
        self.username = username
        self.role = role
        self.authenticated = False

    def is_active(self):
        return True

    def get_id(self):
        return self.username

    def is_authenticated(self):
        return self.authenticated

    def is_anonymous(self):
        return False

# GECORRIGEERD: Flask-Login user loader


@login_manager.user_loader
def load_user(user_id):
    try:
        if not mongo:
            return None
        # GECORRIGEERD: Gebruik consistente database referentie
        user = mongo.db['users'].find_one({"username": user_id})
        if user:
            user_obj = User(user["username"], user.get('role', 'user'))
            user_obj.authenticated = True
            return user_obj
        return None
    except Exception as e:
        log_error(f"Error loading user: {e}")
        return None

# GECORRIGEERD: Health check endpoint


@app.route(f'{endpoint}/health', methods=['GET'])
def health_check():
    try:
        if mongo:
            result = mongo.db.command('ping')
            response = {
                "status": "healthy",
                "mongodb": "connected",
                "database": mongo.db.name,
                "environment": "docker" if in_docker else "local",
                "timestamp": datetime.utcnow().isoformat()
            }
            return jsonify(response), 200
        else:
            response = {
                "status": "unhealthy",
                "mongodb": "not connected",
                "environment": "docker" if in_docker else "local",
                "timestamp": datetime.utcnow().isoformat()
            }
            return jsonify(response), 500
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "mongodb": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

# GECORRIGEERD: Users endpoints met consistente database referenties


@app.route(f'{endpoint}/users/', methods=['GET'])
def get_users():
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        # GECORRIGEERD: Gebruik mongo.db in plaats van mongo.cx
        users = mongo.db['users'].find()
        user_list = []
        for user in users:
            user_list.append({
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'company_name': user.get('company_name', ''),
                'user_role': user.get('role', 'user'),
                'username': user.get('username', ''),
                'email': user.get('email', ''),
                "blocked": user.get('blocked', False)
            })

        return jsonify(users=user_list), 200
    except Exception as e:
        log_error(f"Error retrieving users: {e}")
        return jsonify({'error': str(e)}), 500


@app.route(f'{endpoint}/users/<username>', methods=['GET'])
def get_user(username):
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        # GECORRIGEERD: Gebruik mongo.db
        user = mongo.db['users'].find_one({"username": username})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_data = {
            'user_id': str(user['_id']),
            'first_name': user.get('first_name', ''),
            'last_name': user.get('last_name', ''),
            'company_name': user.get('company_name', ''),
            'user_role': user.get('role', 'user'),
            'username': user.get('username', ''),
            'email': user.get('email', ''),
            "blocked": user.get('blocked', False)
        }
        return jsonify(user_data), 200
    except Exception as e:
        log_error(f"Error retrieving user {username}: {e}")
        return jsonify({'error': str(e)}), 500

# GECORRIGEERD: Login endpoint


@app.route(f'{endpoint}/login', methods=["POST"])
def login():
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        data = request.get_json()
        username_or_email = data.get('username')
        password = data.get('password')

        if not username_or_email or not password:
            return jsonify({"message": "Username and password are required."}), 400

        # GECORRIGEERD: Gebruik mongo.db
        user = mongo.db['users'].find_one({
            "$or": [
                {"username": username_or_email},
                {"email": username_or_email}
            ]
        })

        if user and bcrypt.checkpw(password.encode("utf-8"), user['password'].encode("utf-8")):
            if user.get("blocked", False):
                return jsonify({"message": "Account is blocked."}), 403

            user_obj = User(user["username"], user.get('role', 'user'))
            login_user(user_obj)
            log_info(f"User successfully logged in: {user['username']}")
            return jsonify({
                "username": user["username"],
                "role": user.get('role', 'user')
            }), 200
        else:
            return jsonify({"message": "Invalid login credentials."}), 401
    except Exception as e:
        log_error(f"Error during login: {e}")
        return jsonify({"message": "An error occurred during login."}), 500

# GECORRIGEERD: Create user endpoint


@app.route(f'{endpoint}/users/', methods=["POST"])
def create_user():
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        data = request.get_json()
        username = data.get("username")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        company_name = data.get("company_name")
        password = data.get("password")
        role = data.get("role", "user")
        blocked = data.get("blocked", False)

        if not username or not password or not email:
            return jsonify({"message": "Username, password, and email are required."}), 400

        # Check if username exists - GECORRIGEERD
        if mongo.db['users'].find_one({"username": username}):
            return jsonify({"message": "Username already exists."}), 400

        # Check if email exists - GECORRIGEERD
        if mongo.db['users'].find_one({"email": email}):
            return jsonify({"message": "Email already exists."}), 400

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # GECORRIGEERD: Gebruik mongo.db
        mongo.db['users'].insert_one({
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

# GECORRIGEERD: Admin creation function


def create_default_admin():
    print("=== CREATING DEFAULT ADMIN ===")
    try:
        if not mongo:
            print("✗ MongoDB not connected, cannot create admin user")
            return

        # GECORRIGEERD: Gebruik mongo.db
        existing_admin = mongo.db['users'].find_one({"username": "admin"})
        if not existing_admin:
            hashed_pw = bcrypt.hashpw(
                "admin".encode("utf-8"), bcrypt.gensalt())
            admin_doc = {
                "username": "admin",
                "first_name": "Administrator",
                "last_name": "User",
                "email": "admin@timetracking.local",
                "company_name": "TimeTracking System",
                "password": hashed_pw.decode("utf-8"),
                "role": "admin",
                "blocked": False
            }
            result = mongo.db['users'].insert_one(admin_doc)
            print(f"✓ Admin user created with ID: {result.inserted_id}")
            log_info("Default admin user created")
        else:
            print("✓ Admin user already exists")
    except Exception as e:
        print(f"✗ Error creating default admin: {e}")

# ... je kunt de rest van je routes op dezelfde manier corrigeren ...

# NIEUW: Badge logs endpoints


@app.route(f'{endpoint}/badges/', methods=['GET'])
def get_badges():
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        # Parse query parameters voor filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        month = request.args.get('month')
        day = request.args.get('day')
        badge_code = request.args.get('badge_code')
        user = request.args.get('user')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))

        # Build MongoDB query
        query = {}
        filters_applied = {}

        # Date filtering
        if start_date or end_date:
            date_query = {}
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(
                        start_date.replace('Z', '+00:00'))
                    date_query['$gte'] = start_dt
                    filters_applied['start_date'] = start_date
                except ValueError:
                    return jsonify({'error': 'Invalid start_date format. Use ISO format.'}), 400

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(
                        end_date.replace('Z', '+00:00'))
                    date_query['$lte'] = end_dt
                    filters_applied['end_date'] = end_date
                except ValueError:
                    return jsonify({'error': 'Invalid end_date format. Use ISO format.'}), 400

            query['timestamp'] = date_query

        # Month filtering (1-12)
        if month:
            try:
                month_int = int(month)
                if 1 <= month_int <= 12:
                    query['$expr'] = query.get('$expr', {})
                    query['$expr']['$eq'] = [
                        {'$month': '$timestamp'}, month_int]
                    filters_applied['month'] = month
                else:
                    return jsonify({'error': 'Month must be between 1 and 12.'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid month format.'}), 400

        # Day filtering (1-31)
        if day:
            try:
                day_int = int(day)
                if 1 <= day_int <= 31:
                    if '$expr' not in query:
                        query['$expr'] = {}
                    if '$eq' in query['$expr']:
                        # Combine with existing month filter
                        query['$expr'] = {
                            '$and': [
                                query['$expr'],
                                {'$eq': [{'$dayOfMonth': '$timestamp'}, day_int]}
                            ]
                        }
                    else:
                        query['$expr']['$eq'] = [
                            {'$dayOfMonth': '$timestamp'}, day_int]
                    filters_applied['day'] = day
                else:
                    return jsonify({'error': 'Day must be between 1 and 31.'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid day format.'}), 400

        # Badge code filtering
        if badge_code:
            query['badge_code'] = {'$regex': badge_code,
                                   '$options': 'i'}  # Case insensitive
            filters_applied['badge_code'] = badge_code

        # User filtering
        if user:
            query['$or'] = [
                {'username': {'$regex': user, '$options': 'i'}},
                {'user_id': {'$regex': user, '$options': 'i'}},
                {'first_name': {'$regex': user, '$options': 'i'}},
                {'last_name': {'$regex': user, '$options': 'i'}}
            ]
            filters_applied['user'] = user

        # Get total count for pagination
        total_count = mongo.db['badge_logs'].count_documents(query)

        # Execute query with pagination
        skip = (page - 1) * limit
        badges_cursor = mongo.db['badge_logs'].find(
            query).sort('timestamp', -1).skip(skip).limit(limit)

        badge_list = []
        for badge in badges_cursor:
            badge_data = {
                'id': str(badge['_id']),
                'badge_code': badge.get('badge_code', ''),
                'timestamp': badge.get('timestamp').isoformat() if badge.get('timestamp') else None,
                'username': badge.get('username', ''),
                'user_id': badge.get('user_id', ''),
                'first_name': badge.get('first_name', ''),
                'last_name': badge.get('last_name', ''),
                # 'scan_in', 'scan_out', etc.
                'action': badge.get('action', ''),
                'location': badge.get('location', ''),
                'device_id': badge.get('device_id', ''),
                'raw_data': badge.get('raw_data', {}),
                'processed': badge.get('processed', False)
            }
            badge_list.append(badge_data)

        # Pagination info
        total_pages = (total_count + limit - 1) // limit

        response = {
            'badges': badge_list,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_count': total_count,
                'page_size': limit,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'filters_applied': filters_applied,
            'query_summary': {
                'total_badges': total_count,
                'filtered_badges': len(badge_list),
                'page_info': f"Page {page} of {total_pages}"
            }
        }

        return jsonify(response), 200

    except Exception as e:
        log_error(f"Error retrieving badge logs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route(f'{endpoint}/badges/<badge_id>', methods=['GET'])
def get_badge_by_id(badge_id):
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        try:
            badge_obj_id = ObjectId(badge_id)
        except:
            return jsonify({'error': 'Invalid badge ID format'}), 400

        badge = mongo.db['badge_logs'].find_one({"_id": badge_obj_id})
        if not badge:
            return jsonify({'error': 'Badge log not found'}), 404

        badge_data = {
            'id': str(badge['_id']),
            'badge_code': badge.get('badge_code', ''),
            'timestamp': badge.get('timestamp').isoformat() if badge.get('timestamp') else None,
            'username': badge.get('username', ''),
            'user_id': badge.get('user_id', ''),
            'first_name': badge.get('first_name', ''),
            'last_name': badge.get('last_name', ''),
            'action': badge.get('action', ''),
            'location': badge.get('location', ''),
            'device_id': badge.get('device_id', ''),
            'raw_data': badge.get('raw_data', {}),
            'processed': badge.get('processed', False),
            'created_at': badge.get('created_at').isoformat() if badge.get('created_at') else None,
            'updated_at': badge.get('updated_at').isoformat() if badge.get('updated_at') else None
        }

        return jsonify(badge_data), 200

    except Exception as e:
        log_error(f"Error retrieving badge {badge_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route(f'{endpoint}/badges/stats', methods=['GET'])
def get_badge_stats():
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        # Get date range for filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Build base query
        match_query = {}
        if start_date or end_date:
            date_query = {}
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(
                        start_date.replace('Z', '+00:00'))
                    date_query['$gte'] = start_dt
                except ValueError:
                    return jsonify({'error': 'Invalid start_date format'}), 400

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(
                        end_date.replace('Z', '+00:00'))
                    date_query['$lte'] = end_dt
                except ValueError:
                    return jsonify({'error': 'Invalid end_date format'}), 400

            match_query['timestamp'] = date_query

        # Aggregation pipeline voor statistieken
        pipeline = [
            {'$match': match_query},
            {
                '$group': {
                    '_id': None,
                    'total_badges': {'$sum': 1},
                    'unique_users': {'$addToSet': '$username'},
                    'unique_badge_codes': {'$addToSet': '$badge_code'},
                    'actions': {'$push': '$action'},
                    'devices': {'$addToSet': '$device_id'},
                    'earliest_scan': {'$min': '$timestamp'},
                    'latest_scan': {'$max': '$timestamp'}
                }
            },
            {
                '$project': {
                    'total_badges': 1,
                    'unique_users_count': {'$size': '$unique_users'},
                    'unique_badge_codes_count': {'$size': '$unique_badge_codes'},
                    'unique_devices_count': {'$size': '$devices'},
                    'earliest_scan': 1,
                    'latest_scan': 1,
                    'unique_users': 1,
                    'unique_badge_codes': 1,
                    'devices': 1
                }
            }
        ]

        result = list(mongo.db['badge_logs'].aggregate(pipeline))

        if result:
            stats = result[0]

            # Count actions
            actions_pipeline = [
                {'$match': match_query},
                {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]
            action_stats = list(
                mongo.db['badge_logs'].aggregate(actions_pipeline))

            # Daily activity
            daily_pipeline = [
                {'$match': match_query},
                {
                    '$group': {
                        '_id': {
                            'year': {'$year': '$timestamp'},
                            'month': {'$month': '$timestamp'},
                            'day': {'$dayOfMonth': '$timestamp'}
                        },
                        'count': {'$sum': 1}
                    }
                },
                {'$sort': {'_id': 1}},
                {'$limit': 30}  # Last 30 days
            ]
            daily_stats = list(
                mongo.db['badge_logs'].aggregate(daily_pipeline))

            response = {
                'total_badges': stats.get('total_badges', 0),
                'unique_users': stats.get('unique_users_count', 0),
                'unique_badge_codes': stats.get('unique_badge_codes_count', 0),
                'unique_devices': stats.get('unique_devices_count', 0),
                'earliest_scan': stats.get('earliest_scan').isoformat() if stats.get('earliest_scan') else None,
                'latest_scan': stats.get('latest_scan').isoformat() if stats.get('latest_scan') else None,
                'action_breakdown': {item['_id']: item['count'] for item in action_stats},
                'daily_activity': [
                    {
                        'date': f"{item['_id']['year']}-{item['_id']['month']:02d}-{item['_id']['day']:02d}",
                        'count': item['count']
                    } for item in daily_stats
                ],
                'user_list': stats.get('unique_users', []),
                'badge_codes': stats.get('unique_badge_codes', []),
                'devices': stats.get('devices', [])
            }
        else:
            response = {
                'total_badges': 0,
                'unique_users': 0,
                'unique_badge_codes': 0,
                'unique_devices': 0,
                'earliest_scan': None,
                'latest_scan': None,
                'action_breakdown': {},
                'daily_activity': [],
                'user_list': [],
                'badge_codes': [],
                'devices': []
            }

        return jsonify(response), 200

    except Exception as e:
        log_error(f"Error retrieving badge statistics: {e}")
        return jsonify({'error': str(e)}), 500


@app.route(f'{endpoint}/badges/', methods=['POST'])
def create_badge_log():
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        data = request.get_json()

        # Required fields
        badge_code = data.get('badge_code')
        action = data.get('action', 'scan')

        if not badge_code:
            return jsonify({'error': 'badge_code is required'}), 400

        # Optional fields
        username = data.get('username', '')
        user_id = data.get('user_id', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        location = data.get('location', '')
        device_id = data.get('device_id', '')
        raw_data = data.get('raw_data', {})

        # Create badge log document
        badge_log = {
            'badge_code': badge_code,
            'timestamp': datetime.utcnow(),
            'username': username,
            'user_id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'action': action,
            'location': location,
            'device_id': device_id,
            'raw_data': raw_data,
            'processed': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = mongo.db['badge_logs'].insert_one(badge_log)

        log_info(f"Badge log created: {badge_code} - {action}")

        return jsonify({
            'message': 'Badge log created successfully',
            'id': str(result.inserted_id),
            'badge_code': badge_code,
            'timestamp': badge_log['timestamp'].isoformat()
        }), 201

    except Exception as e:
        log_error(f"Error creating badge log: {e}")
        return jsonify({'error': str(e)}), 500


@app.route(f'{endpoint}/badges/<badge_id>', methods=['PUT'])
def update_badge_log(badge_id):
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        try:
            badge_obj_id = ObjectId(badge_id)
        except:
            return jsonify({'error': 'Invalid badge ID format'}), 400

        data = request.get_json()

        # Fields that can be updated
        update_fields = {}
        updatable_fields = ['processed', 'username', 'user_id',
                            'first_name', 'last_name', 'action', 'location']

        for field in updatable_fields:
            if field in data:
                update_fields[field] = data[field]

        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400

        update_fields['updated_at'] = datetime.utcnow()

        result = mongo.db['badge_logs'].update_one(
            {'_id': badge_obj_id},
            {'$set': update_fields}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Badge log not found'}), 404

        log_info(f"Badge log updated: {badge_id}")
        return jsonify({'message': 'Badge log updated successfully'}), 200

    except Exception as e:
        log_error(f"Error updating badge log {badge_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route(f'{endpoint}/badges/<badge_id>', methods=['DELETE'])
def delete_badge_log(badge_id):
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        try:
            badge_obj_id = ObjectId(badge_id)
        except:
            return jsonify({'error': 'Invalid badge ID format'}), 400

        result = mongo.db['badge_logs'].delete_one({'_id': badge_obj_id})

        if result.deleted_count == 0:
            return jsonify({'error': 'Badge log not found'}), 404

        log_info(f"Badge log deleted: {badge_id}")
        return jsonify({'message': 'Badge log deleted successfully'}), 200

    except Exception as e:
        log_error(f"Error deleting badge log {badge_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route(f'{endpoint}/badges/search', methods=['POST'])
def search_badges():
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        data = request.get_json()
        filter_params = data.get('filters', {})
        limit = data.get('limit', 50)  # Standaard laatste 50
        # Standaard nieuwste eerst
        sort_params = data.get('sort', {'timestamp': -1})

        # Parse filter parameters
        start_date = filter_params.get('start_date')
        end_date = filter_params.get('end_date')
        month = filter_params.get('month')
        day = filter_params.get('day')
        badge_code = filter_params.get('badge_code')
        user = filter_params.get('user')

        # Build MongoDB query
        query = {}
        filters_applied = {}

        # Date filtering
        if start_date or end_date:
            date_query = {}
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(
                        start_date.replace('Z', '+00:00'))
                    date_query['$gte'] = start_dt
                    filters_applied['start_date'] = start_date
                except ValueError:
                    return jsonify({'error': 'Invalid start_date format. Use ISO format.'}), 400

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(
                        end_date.replace('Z', '+00:00'))
                    date_query['$lte'] = end_dt
                    filters_applied['end_date'] = end_date
                except ValueError:
                    return jsonify({'error': 'Invalid end_date format. Use ISO format.'}), 400

            query['timestamp'] = date_query

        # Month filtering (1-12)
        if month:
            try:
                month_int = int(month)
                if 1 <= month_int <= 12:
                    query['$expr'] = query.get('$expr', {})
                    query['$expr']['$eq'] = [
                        {'$month': '$timestamp'}, month_int]
                    filters_applied['month'] = month
                else:
                    return jsonify({'error': 'Month must be between 1 and 12.'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid month format.'}), 400

        # Day filtering (1-31)
        if day:
            try:
                day_int = int(day)
                if 1 <= day_int <= 31:
                    if '$expr' not in query:
                        query['$expr'] = {}
                    if '$eq' in query['$expr']:
                        # Combine with existing month filter
                        query['$expr'] = {
                            '$and': [
                                query['$expr'],
                                {'$eq': [{'$dayOfMonth': '$timestamp'}, day_int]}
                            ]
                        }
                    else:
                        query['$expr']['$eq'] = [
                            {'$dayOfMonth': '$timestamp'}, day_int]
                    filters_applied['day'] = day
                else:
                    return jsonify({'error': 'Day must be between 1 and 31.'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid day format.'}), 400

        # Badge code filtering
        if badge_code:
            query['badge_code'] = {'$regex': badge_code,
                                   '$options': 'i'}  # Case insensitive
            filters_applied['badge_code'] = badge_code

        # User filtering
        if user:
            query['$or'] = [
                {'username': {'$regex': user, '$options': 'i'}},
                {'user_id': {'$regex': user, '$options': 'i'}},
                {'first_name': {'$regex': user, '$options': 'i'}},
                {'last_name': {'$regex': user, '$options': 'i'}}
            ]
            filters_applied['user'] = user

        # Execute query met limit voor laatste X records
        badges_cursor = mongo.db['badge_logs'].find(
            query).sort('timestamp', -1).limit(limit)

        badge_list = []
        for badge in badges_cursor:
            badge_data = {
                'id': str(badge['_id']),
                'badgecode': badge.get('badge_code', ''),
                'badge_code': badge.get('badge_code', ''),
                'timestamp': badge.get('timestamp').isoformat() if badge.get('timestamp') else None,
                'scan_time': badge.get('timestamp').isoformat() if badge.get('timestamp') else None,
                'user': badge.get('username', ''),
                'username': badge.get('username', ''),
                'user_id': badge.get('user_id', ''),
                'first_name': badge.get('first_name', ''),
                'last_name': badge.get('last_name', ''),
                'action': badge.get('action', ''),
                'location': badge.get('location', ''),
                'device_id': badge.get('device_id', ''),
                'raw_data': badge.get('raw_data', {}),
                'processed': badge.get('processed', False)
            }
            badge_list.append(badge_data)

        response = {
            'badges': badge_list,
            'filters_applied': filters_applied,
            'query_summary': {
                'total_badges': len(badge_list),
                'limit': limit,
                'info': f"Latest {len(badge_list)} badge scans" + (" (filtered)" if filters_applied else "")
            }
        }

        return jsonify(response), 200

    except Exception as e:
        log_error(f"Error searching badge logs: {e}")
        return jsonify({'error': str(e)}), 500

# NIEUW: Bulk operations voor badge logs


@app.route(f'{endpoint}/badges/bulk/mark-processed', methods=['POST'])
def bulk_mark_processed():
    try:
        if not mongo:
            return jsonify({'error': 'Database not connected'}), 500

        data = request.get_json()
        badge_ids = data.get('badge_ids', [])

        if not badge_ids:
            return jsonify({'error': 'badge_ids array is required'}), 400

        # Convert to ObjectIds
        try:
            object_ids = [ObjectId(bid) for bid in badge_ids]
        except:
            return jsonify({'error': 'Invalid badge ID format in array'}), 400

        result = mongo.db['badge_logs'].update_many(
            {'_id': {'$in': object_ids}},
            {
                '$set': {
                    'processed': True,
                    'updated_at': datetime.utcnow()
                }
            }
        )

        log_info(
            f"Bulk marked {result.modified_count} badge logs as processed")
        return jsonify({
            'message': f'Marked {result.modified_count} badge logs as processed',
            'modified_count': result.modified_count
        }), 200

    except Exception as e:
        log_error(f"Error in bulk mark processed: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print(f"\n=== STARTING FLASK APP ===")
    print(f"Environment: {'Docker' if in_docker else 'Local'}")
    print(f"MongoDB Status: {'Connected' if mongo else 'Not Connected'}")

    try:
        create_default_admin()
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"✗ Error starting Flask app: {e}")
    except KeyboardInterrupt:
        print("\n=== SHUTTING DOWN ===")
        print("Flask app shutting down...")
