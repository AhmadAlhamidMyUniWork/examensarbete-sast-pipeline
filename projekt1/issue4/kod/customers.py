from flask import Blueprint, jsonify
from database import get_all_customers
from middleware import token_required

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('/customers', methods=['GET'])
@token_required
def get_customers():
    customers = get_all_customers()
    return jsonify({'customers': customers}), 200
