from flask import Blueprint, abort, jsonify, current_app
from gql import gql

gql_imp = Blueprint('gql_imp', __name__)


@gql_imp.route('/api/products')
def products():
    client = current_app.config["gql_client"]
    query = gql('''
        query allProducts {
          allProducts {
            id
            sku
            name
            stock
          }
        }
    ''')
    result = client.execute(query)
    return jsonify(result["allProducts"])