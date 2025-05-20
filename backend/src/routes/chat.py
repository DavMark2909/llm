from flask import Blueprint, request, jsonify
from flask import jsonify
from flask_jwt_extended import (
    jwt_required, get_jwt_identity
)
from flask import current_app


from sqlalchemy.exc import IntegrityError

from model import User, Chat, Message
from db import db
from socket_handler import sendToUser
from threading import Thread
import os

from routes.utils.file_converter import convert_files
from routes.utils.response_starter import parse_question
from routes.utils.schema_extractor import get_table_schemas
from routes.utils.fact_table_starter import launch_fact_table_agent

import json


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
    
    messages = [{'content': message.content, 'human': message.human, 'id': message.id, 'file': message.file} for message in chat.messages]
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
            "name": chat.topic
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@message_bp.route('/send-file', methods=['POST'])
@jwt_required()
def recieve_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    chat_id = request.form.get('chat_id')
    extension = request.form.get('extension')

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    UPLOAD_FOLDER = './uploads'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    save_message(chat_id=chat_id, content=file.filename, file=True)

    return jsonify({
        'content': file.filename,
        'file' : True,
        'human' : True,
    }), 200

@message_bp.route('/convert-files', methods=['GET'])
@jwt_required()
def convert_files_endpoint():
    UPLOAD_FOLDER = './uploads'
    full_path = os.path.abspath(UPLOAD_FOLDER)
    result = convert_files(full_path)

    if result == "success":
        return jsonify({
            'content': "Your files have been succesfully uploaded and converted",
            'file' : False,
            'human' : False,
        }), 200
    else:
        return jsonify({
            'content': "The error occured while trying to upload your files. Please try later",
            'file' : False,
            'human' : False,
        }), 500

@message_bp.route('/generate-star-schema/<int:chat_id>', methods=['GET'])
@jwt_required()
def generate_star_schema(chat_id):
    schema = get_table_schemas()
    storage = f"Stored tables are: {list(schema.keys())}"
    save_message(chat_id, storage, human=False)
    return jsonify({
        'content': schema,
        'file' : False,
        'human' : False,
        'type': "star_schema_interactive"
    }), 200

@message_bp.route('/star-schema/<int:chat_id>', methods=['GET'])
@jwt_required()
def do_star_schema(chat_id):
    agg_columns = request.args.getlist('agg_columns')
    operations = request.args.get('operations')  # this may come as a stringified dict
    time_column = request.args.get('time_column')
    time = request.args.get('time')

    print("Got the message")
    print(agg_columns)
    print(operations)
    print(time_column)
    print(time)

    if operations:
        operations = json.loads(operations)

    result = launch_fact_table_agent(agg_columns, operations, time_column, time)

    if result == "success":
        return jsonify({
            'content': "Fact table was succesfully generated",
            'file' : False,
            'human' : False,
        }), 200
    else:
        return jsonify({
            'content': "The error occured while trying to create fact table. Please repeat once again",
            'file' : False,
            'human' : False,
        }), 500


@message_bp.route('/send/<int:chat_id>', methods=['POST'])
@jwt_required()
def receive_message(chat_id):

    data = request.get_json()
    content = data.get('content')
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    if not content:
        return jsonify({'message': 'Message content is required!'}), 400

    id = save_message(chat_id=chat_id, content=content)

    thread = Thread(target=process_in_thread, args=(user.id, chat_id, content))
    thread.start()

    return jsonify({
        'content': content,
        'file' : False,
        'human' : True,
        'id': id
    }), 200



def save_message(chat_id, content, file=False, human=True):
    new_message = Message(
        chat_id=chat_id,
        content=content,
        human=human,
        file=file
    )

    db.session.add(new_message)
    db.session.commit()

    return new_message.id

def processMessage(userId, chatId, content):
    # some stuff here with langchain
    (response, type) = parse_question(content)
    if type == "chart":
        s = ', '.join(str(x) for x in response) 
        id = save_message(chat_id=chatId, content=s, human=False)
    else:
        id = save_message(chat_id=chatId, content=response, human=False)
    sendToUser(userId, response, type, id)

def process_in_thread(user_id, chat_id, content):
    from main import app
    with app.app_context():
        processMessage(user_id, chat_id, content)
