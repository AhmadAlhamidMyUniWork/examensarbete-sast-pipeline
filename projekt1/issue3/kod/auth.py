import jwt
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from database import create_user, get_user_by_username
from config import Config

auth_bp = Blueprint('auth', __name__)


def _generate_token(user_id, username):
    payload = {
        'sub': user_id,
        'username': username,
        'exp': datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc),
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'username och password krävs'}), 400

    if get_user_by_username(username):
        return jsonify({'error': 'användarnamnet är redan taget'}), 409

    create_user(username, password)
    return jsonify({'message': 'användare skapad'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or password:
        return jsonify({'error': 'username och password krävs'}), 400

    user = get_user_by_username(username)
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'felaktigt användarnamn eller lösenord'}), 401

    token = _generate_token(user['id'], user['username'])
    return jsonify({'token': token}), 200
