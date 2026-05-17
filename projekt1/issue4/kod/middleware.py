import jwt
from functools import wraps
from flask import request, jsonify, g
from config import Config


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'token saknas'}), 401

        token = auth_header.split(' ', 1)[1]

        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            g.current_user = {'id': payload['sub'], 'username': payload['username']}
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'token har gått ut'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'ogiltig token'}), 401

        return f(*args, **kwargs)
    return decorated
