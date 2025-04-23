import json
from flask import Flask, jsonify, request
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'temp-uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if data is None:
        return jsonify({'error': 'The provided user is wrong'}), 400
    return jsonify({'user': 'Mark'}), 200

@app.route('/upload', methods=['POST'])
def get_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    upload_file(file_path)
    return jsonify({'message': f'File {file.filename} uploaded successfully'}), 200

def upload_file():
    return ""


    
