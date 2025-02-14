import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, static_folder='../images')
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "default_secret")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        "DATABASE_URI", "sqlite:///quiz.db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = os.environ.get("DEBUG", "False") == "True"

    db.init_app(app)

    # Set up logging to file
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler(
        'logs/flask.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    # Redirect werkzeug logs to file by removing its default handlers:
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers.clear()  # Remove default stdout handlers
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.setLevel(logging.INFO)

    app.logger.info('Flask app startup')

    # Initialize your database etc.
    with app.app_context():
        from app import models  # noqa
        db.create_all()

    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
