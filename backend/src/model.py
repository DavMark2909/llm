from db import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, unique=True, nullable=False)
    name = db.Column(db.Text, nullable=False)
    hash = db.Column(db.Text, nullable=False)

    chats = db.relationship('Chat', back_populates='user')

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # chat ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.Text, nullable=False)

    user = db.relationship('User', back_populates='chats')    
    messages = db.relationship('Message', back_populates='chat', cascade='all, delete-orphan')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    human = db.Column(db.Boolean, nullable=False)  
    file = db.Column(db.Boolean, nullable=False)  

    chat = db.relationship('Chat', back_populates='messages')
