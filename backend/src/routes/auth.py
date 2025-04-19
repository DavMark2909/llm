from flask import Blueprint, request, jsonify
from flask import jsonify
import bcrypt
from flask_jwt_extended import (
    jwt_required, create_access_token,
    get_jwt_identity, set_access_cookies,
    unset_jwt_cookies
)

from sqlalchemy.exc import IntegrityError

from model import User
from db import db


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['POST'])
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

        access_token = create_access_token(identity=email)
        response = jsonify({"name": name})
        set_access_cookies(response, access_token)
        return response
        # return {"access_token": access_token}, 200
    except IntegrityError:
        db.session.rollback()
        return 'User Already Exists', 400
    except AttributeError:
        return 'Provide an Email and Password in JSON format in the request body', 400
    

@auth_bp.route('/login', methods=['POST'])
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
            response = jsonify({"name": user.name})
            access_token = create_access_token(identity=email)
            set_access_cookies(response, access_token)
            # return {"access_token": access_token}, 200
            return response
        else:
            return 'Invalid Login Info!', 400
    except AttributeError:
        return 'Provide an Email and Password in JSON format in the request body', 400
    
@auth_bp.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response
    
@auth_bp.route('/check', methods=['GET', 'OPTIONS'])
@jwt_required()
def check_auth():
    user = get_jwt_identity()
    return jsonify({
        "user": user
    }), 200