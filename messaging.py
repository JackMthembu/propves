from flask import Blueprint, render_template, request, jsonify
from models import db, User, Message

messaging_bp = Blueprint('messaging', __name__)

@messaging_bp.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    new_message = Message(
        sender_id=data['sender_id'],
        recipient_id=data['recipient_id'],
        content=data['content']
    )
    db.session.add(new_message)
    db.session.commit()
    return jsonify({'message': 'Message sent successfully!'}), 201

@messaging_bp.route('/messages/<int:user_id>', methods=['GET'])
def get_messages(user_id):
    # Query messages sent or received by user_id
    messages = Message.query.filter(
        (Message.sender_id == user_id) | (Message.recipient_id == user_id)
    ).order_by(Message.timestamp.desc()).all()

    # Build a list of dictionaries with enriched data
    results = []
    for msg in messages:
        sender = User.query.get(msg.sender_id)
        recipient = User.query.get(msg.recipient_id)
        # Truncate the message content for a preview
        preview = msg.content[:60] + ('...' if len(msg.content) > 60 else '')
        results.append({
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_username': sender.username if sender else 'Unknown',
            'sender_profile_picture': sender.profile_picture if sender else 'default.png',
            'recipient_id': msg.recipient_id,
            'recipient_username': recipient.username if recipient else 'Unknown',
            'content': msg.content,
            'preview': preview,
            'timestamp': msg.timestamp.isoformat()
        })
    return jsonify(results), 200

@messaging_bp.route('/inbox')
def inbox():
    # For demonstration, let's assume the logged-in user_id is passed via query param (or session)
    user_id = request.args.get('user_id', 1, type=int)  
    return render_template('inbox.html', user_id=user_id)
