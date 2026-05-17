import requests
from flask import Blueprint, jsonify
from middleware import token_required
from config import Config

external_bp = Blueprint('external', __name__)


def _fetch_external_data():
    response = requests.get(
        Config.EXTERNAL_API_URL,
        timeout=Config.EXTERNAL_API_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


@external_bp.route('/external', methods=['GET'])
@token_required
def get_external():
    try:
        data = _fetch_external_data()
        return jsonify({'source': Config.EXTERNAL_API_URL, 'data': data}), 200

    except requests.Timeout:
        return jsonify({'error': 'extern tjänst svarade inte i tid'}), 504

    except requests.HTTPError as e:
        status = e.response.status_code
        return jsonify({'error': f'extern tjänst returnerade fel: {status}'}), 502

    except requests.ConnectionError:
        return jsonify({'error': 'kunde inte ansluta till extern tjänst'}), 502

    except requests.RequestException as e:
        return jsonify({'error': f'oväntat fel vid externt anrop: {str(e)}'}), 502
