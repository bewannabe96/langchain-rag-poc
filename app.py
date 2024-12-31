import json
import os
import uuid
from datetime import datetime
from typing import Generator, Optional

from flask import Flask, request, Response, jsonify, g
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from langchain_core.messages import HumanMessage, AIMessage
from pymongo import MongoClient
from pymongo.collection import Collection

from langchain_rag.chatbot import chatbot
from langchain_rag.message.base import BaseCustomMessage

app = Flask(__name__)
CORS(app)
api = Api(app, version='1.0',
          title='DayTrip Chatbot API',
          description='DayTrip Chatbot REST API with SSE',
          doc='/swagger')

# Namespaces
ns_health = api.namespace('health', description='Health check operations')
ns_session = api.namespace('sessions', description='Session operations')
ns_chat = api.namespace('chat', description='Chat operations')

# Models
session_model = api.model('Session', {
    'user_id': fields.String(required=True, description='User ID'),
    'language': fields.String(default='Korean', description='Chat language')
})

session_response = api.model('SessionResponse', {
    'session_id': fields.String(description='Session ID'),
    'user_id': fields.String(description='User ID'),
    'language': fields.String(description='Chat language'),
    'messages': fields.List(fields.Raw, description='Chat messages'),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'updated_at': fields.DateTime(description='Last update timestamp')
})

chat_request = api.model('ChatRequest', {
    'session_id': fields.String(required=True, description='Session ID'),
    'content': fields.String(required=True, description='Message content')
})

chat_response = api.model('ChatResponse', {
    'id': fields.String(required=True, description='Unique message identifier'),
    'source': fields.String(required=True, description='Message source'),
    'type': fields.String(required=True, description='Message type (text, text_chunk, etc.)'),
    'content': fields.String(required=True, description='Message content chunk')
})


# MongoDB connection functions
def get_db() -> MongoClient:
    if 'db' not in g:
        g.db = MongoClient(os.getenv('SESSION_MONGO_CONN_STR'))
    return g.db


def get_sessions() -> Collection:
    db = get_db()
    sessions = db['daytrip_chatbot']['session']
    return sessions


@ns_session.route('')
class SessionResource(Resource):
    @ns_session.expect(session_model)
    @ns_session.marshal_with(session_response, code=201)
    def post(self):
        """Create a new chat session"""
        data = request.json

        if 'user_id' not in data:
            api.abort(400, 'User ID is required')

        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'user_id': data['user_id'],
            'language': data.get('language', 'Korean'),
            'messages': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        get_sessions().insert_one(session_data)
        return session_data, 201


@ns_session.route('/user/<string:user_id>')
class UserSessionResource(Resource):
    @ns_session.marshal_list_with(session_response)
    def get(self, user_id):
        """Get all sessions for a user"""
        user_sessions = get_sessions().find(
            {'user_id': user_id},
            {'messages': 0}
        ).sort('updated_at', -1)

        return list(user_sessions)


@ns_session.route('/<string:session_id>')
class SessionDetailResource(Resource):
    @ns_session.marshal_with(session_response)
    def get(self, session_id):
        """Get session details"""
        session = get_sessions().find_one({'session_id': session_id})
        if not session:
            api.abort(404, 'Session not found')
        return session


@ns_chat.route('')
class ChatResource(Resource):
    @ns_chat.expect(chat_request)
    @ns_chat.produces(['text/event-stream'])
    @ns_chat.response(200, 'Success', headers={
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    }, model=chat_response)
    def post(self):
        """Send a chat message and receive streaming response"""
        data = request.json
        session_id = data.get('session_id')
        content = data.get('content')

        session = get_sessions().find_one({'session_id': session_id})
        if not session:
            api.abort(404, 'Invalid session')

        app_context = app.app_context()

        def generate() -> Generator[str, None, None]:
            with app_context:
                message_id = str(uuid.uuid4())
                get_sessions().update_one(
                    {'session_id': session_id},
                    {
                        '$push': {'messages': {
                            'message_id': message_id,
                            'role': 'user',
                            'content': content,
                            'timestamp': datetime.utcnow()
                        }},
                        '$set': {'updated_at': datetime.utcnow()}
                    },
                )

                response = {'id': message_id, 'source': 'user', 'type': 'message', 'content': content}
                yield f"data: {json.dumps(response)}\n\n"

                streamer = chatbot.stream(
                    {
                        "messages": [HumanMessage(content)],
                        "language": session['language'],
                        "service_switch": True,
                        "agent_calls": []
                    },
                    {"configurable": {"thread_id": session_id}},
                    stream_mode="messages"
                )

                message: Optional[dict[str, any]] = None
                for chunk, _ in streamer:
                    if chunk.content == "":
                        continue
                    elif not (isinstance(chunk, AIMessage) or isinstance(chunk, BaseCustomMessage)):
                        continue

                    if message is None or message['message_id'] != chunk.id:
                        if message is not None:
                            get_sessions().update_one(
                                {'session_id': session_id},
                                {
                                    '$push': {'messages': {**message, 'timestamp': datetime.utcnow()}},
                                    '$set': {'updated_at': datetime.utcnow()}
                                },
                            )
                        message = {'message_id': chunk.id, 'role': 'bot', 'content': '', }

                    message['content'] += chunk.content

                    message_type = "text_chunk"
                    if isinstance(chunk, BaseCustomMessage):
                        message_type = chunk.type.replace(' ', '_')

                    response = {
                        'id': message['message_id'],
                        'source': 'bot',
                        'type': message_type,
                        'content': chunk.content,
                    }
                    yield f"data: {json.dumps(response)}\n\n"

                if message is not None:
                    get_sessions().update_one(
                        {'session_id': session_id},
                        {
                            '$push': {'messages': {**message, 'timestamp': datetime.utcnow()}},
                            '$set': {'updated_at': datetime.utcnow()}
                        },
                    )

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )


@ns_health.route('')
class HealthCheckResource(Resource):
    def get(self):
        """Health check endpoint"""
        return {"status": "OK"}, 200


@app.errorhandler(Exception)
def handle_error(error):
    return jsonify({
        'error': str(error),
        'type': error.__class__.__name__
    }), getattr(error, 'code', 500)


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8765)
