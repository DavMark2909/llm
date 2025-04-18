from flask import Flask, request
from flask import jsonify
import bcrypt
import os
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity
)

from sqlalchemy.exc import IntegrityError

from model import User
from db import db

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'user.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
app.config['JWT_SECRET_KEY'] = 'research-secret-secret' 
jwt = JWTManager(app)

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        email = request.json.get('email', None)
        password = request.json.get('password', None)
        name = request.json.get('name', None)

        if not email:
            return 'Missing email', 400
        if not password:
            return 'Missing password', 400
        if not name: 
            return 'Missing full name', 400
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        user = User(email=email, name=name, hash=hashed)
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=name)
        return {"access_token": access_token}, 200
    except IntegrityError:
        db.session.rollback()
        return 'User Already Exists', 400
    except AttributeError:
        return 'Provide an Email and Password in JSON format in the request body', 400
    

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        email = request.json.get('email', None)
        password = request.json.get('password', None)
        
        if not email:
            return 'Missing email', 400
        if not password:
            return 'Missing password', 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return 'User Not Found!', 404
        

        if bcrypt.checkpw(password.encode('utf-8'), user.hash):
            access_token = create_access_token(identity=user.name)
            return {"access_token": access_token}, 200
        else:
            return 'Invalid Login Info!', 400
    except AttributeError:
        return 'Provide an Email and Password in JSON format in the request body', 400
    
@app.route('/auth/check', methods=['GET'])
@jwt_required()
def check_auth():
    user = get_jwt_identity()
    return jsonify({
        "logged_in": True,
        "user": user
    }), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)