from flask import Flask
from flask_cors import CORS
from .routes.webhooks import webhooks_bp
from .routes.agents import agents_bp
from .routes.agent_test import agent_test_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register blueprints
    app.register_blueprint(webhooks_bp, url_prefix='/webhook')
    app.register_blueprint(agents_bp)  
    app.register_blueprint(agent_test_bp)  

    return app