from flask import Blueprint, request, jsonify
from flask import jsonify
from flask_jwt_extended import (
    jwt_required, get_jwt_identity
)

from sqlalchemy.exc import IntegrityError

from model import User, Chat
from db import db

message_bp = Blueprint('message', __name__, url_prefix='/message')

@message_bp.route('/load-chats', methods=['GET'])
@jwt_required()
def load_chats():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404
    
    chats = [{'chat_id': chat.id, 'name':chat.topic} for chat in user.chats]
    return jsonify(chats), 200

@message_bp.route('/chat/load/<int:chatId>', methods=['GET'])
@jwt_required()
def load_messages(chatId):
    chat = Chat.query.filter_by(id=chatId).first()

    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    
    messages = [{'content': message.content, 'human': message.human} for message in chat.messages]
    return jsonify(messages), 200

@message_bp.route('/chat/create', methods=['POST'])
@jwt_required()
def create_chat():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    try:
        chat = Chat(user_id=user.id, topic="Current chat")
        db.session.add(chat)
        db.session.commit()

        return jsonify({
            "chat_id": chat.id,
            "topic": chat.topic
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


