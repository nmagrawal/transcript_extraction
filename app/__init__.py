# app/__init__.py
from flask import Flask

def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/')
    return app