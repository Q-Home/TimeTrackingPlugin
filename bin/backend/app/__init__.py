import logging
from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo
from dotenv import load_dotenv

from app.config import Config
from app.extensions import jwt
from app.errors import register_error_handlers
from app.swagger import init_swagger

from app.repositories.log_repository import LogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.badge_repository import BadgeRepository

from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.badge_service import BadgeService
from app.services.index_service import IndexService

from app.routes.auth_routes import register_auth_routes
from app.routes.user_routes import register_user_routes
from app.routes.badge_routes import register_badge_routes
from app.routes.health_routes import register_health_routes
from app.services.timesheet_service import TimesheetService
from app.routes.timesheet_routes import register_timesheet_routes
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/*": {"origins": Config.get_cors_origins()}})
    jwt.init_app(app)
    init_swagger(app)

    mongo = PyMongo(app)

    log_repository = LogRepository(mongo)
    user_repository = UserRepository(mongo)
    badge_repository = BadgeRepository(mongo)

    auth_service = AuthService(user_repository, log_repository)
    user_service = UserService(user_repository, badge_repository, log_repository)
    badge_service = BadgeService(badge_repository, log_repository)
    index_service = IndexService(user_repository, badge_repository, log_repository)
    timesheet_service = TimesheetService(badge_repository)

    app.register_blueprint(register_auth_routes(auth_service, Config.API_PREFIX))
    app.register_blueprint(register_user_routes(user_service, Config.API_PREFIX))
    app.register_blueprint(register_badge_routes(badge_service, Config.API_PREFIX))
    app.register_blueprint(register_health_routes(mongo, Config.API_PREFIX))
    app.register_blueprint(register_timesheet_routes(timesheet_service, Config.API_PREFIX))
    register_error_handlers(app)

    auth_service.create_default_admin()
    index_service.create_indexes()

    logger.info("Application created successfully")
    return app