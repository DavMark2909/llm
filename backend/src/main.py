from datetime import datetime
from datetime import timedelta
from datetime import timezone

from flask import Flask
import os
from flask_jwt_extended import (
    JWTManager, create_access_token,
    get_jwt_identity, get_jwt, set_access_cookies,
)

from flask_cors import CORS
from db import db


from routes.auth import auth_bp
from routes.chat import message_bp
from socket_handler import socketio

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'user.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

app.config['JWT_SECRET_KEY'] = 'research-secret-secret' 
app.config["JWT_COOKIE_SECURE"] = False
app.config['JWT_COOKIE_SAMESITE'] = "Lax"
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_COOKIE_CSRF_PROTECT"] = False

CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5173"])
socketio.init_app(app)
app.register_blueprint(auth_bp)
app.register_blueprint(message_bp)

jwt = JWTManager(app)

@app.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=5))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            set_access_cookies(response, access_token)
        return response
    except (RuntimeError, KeyError):
        return response
    

if __name__ == '__main__':
    socketio.run(app, debug=True)