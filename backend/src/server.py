# from flask import Flask, request
# from flask_socketio import SocketIO, emit
# from dotenv import load_dotenv
# import os

# load_dotenv()
# FLASK_HOST = os.environ.get("FLASK_HOST")
# FLASK_PORT = os.environ.get("FLASK_PORT")
# WEBPACK_DEV_SERVER_URL = os.environ.get("WEBPACK_DEV_SERVER_URL")

# app = Flask(__name__)
# socket = SocketIO(app, cors_allowed_origins=WEBPACK_DEV_SERVER_URL)

# @socket.on("connect")
# def connect():
#     print(f'The connection was established: {request.sid}')

# @socket.on("disconnect")
# def disconnect():
#     print(f'The connection was disconnected: {request.sid}')

# @socket.on("data")
# def handle_data(data):
#     emit("data", {'socketId': request.sid, 'data': data}, broadcast=True)

# if __name__ == "__main__":
#     socket.run(app, host=FLASK_HOST, port=FLASK_PORT)

