from flask import request
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")
user_socket_map = {}

@socketio.on('connect')
def handle_connect():
    user_id = request.args.get('userId')
    print("extracted, ", user_id)
    if user_id:
        user_socket_map[user_id] = request.sid

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    for user_id, stored_sid in list(user_socket_map.items()):
        if stored_sid == sid:
            print(f"User {user_id} disconnected.")
            del user_socket_map[user_id]
            print(f"User {user_id} disconnected")
            break


def get_receiver_socket_id(user_id):
    return user_socket_map.get(str(user_id), None)

def sendToUser(userId, newMessage, id):
    socketId = get_receiver_socket_id(userId)
    if socketId:
        print("foundSocket")
        socketio.emit("newMessage", {'content': newMessage, 'human': False, 'id': id, 'file': False}, room=socketId)
        print("sentMessage")
    else:
        print(f"No socket ID found for user {userId}")