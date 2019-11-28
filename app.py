import datetime
import os
import json

from flask import Flask, jsonify, abort, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.orm import joinedload

from sqlalchemy.sql import func
from elasticapm.contrib.flask import ElasticAPM

from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SQLITE_DB_PATH = 'sqlite:///' + os.path.abspath(os.path.join(BASE_DIR, 'demo', 'db.sql'))


app = Flask(__name__, static_folder=os.path.join("opbeans", "static", "build" ,"static"), template_folder="templates")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', SQLITE_DB_PATH)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ELASTIC_APM'] = {
    'SERVICE_NAME': os.environ.get('ELASTIC_APM_SERVICE_NAME', 'opbeans-flask'),
    'SERVER_URL': os.environ.get('ELASTIC_APM_SERVER_URL', 'http://localhost:8200'),
    'SERVER_TIMEOUT': "10s",
    'DEBUG': True,
}
db = SQLAlchemy(app)
apm = ElasticAPM(app)

#tracing = FlaskTracing(opentracing_tracer, trace_all_requests=True, app=app)


class Customer(db.Model):
    __tablename__ = 'opbeans_customer'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(1000))
    company_name = db.Column(db.String(1000))
    email = db.Column(db.String(1000))
    address = db.Column(db.String(1000))
    postal_code = db.Column(db.String(1000))
    city = db.Column(db.String(1000))
    country = db.Column(db.String(1000))


class Order(db.Model):
    __tablename__ = 'opbeans_order'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('opbeans_customer.id'), nullable=False)
    customer = db.relationship('Customer', backref=db.backref("opbeans_order", lazy=True))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    products = db.relationship('Product', secondary='opbeans_orderline')


class ProductType(db.Model):
    __tablename__ = 'opbeans_producttype'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000), unique=True)

    def __str__(self):
        return self.name


class Product(db.Model):
    __tablename__ = 'opbeans_product'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(1000), unique=True)
    name = db.Column(db.String(1000))
    description = db.Column(db.Text)
    product_type_id = db.Column('product_type_id', db.Integer, db.ForeignKey('opbeans_producttype.id'), nullable=False)
    product_type = db.relationship('ProductType', backref=db.backref('opbeans_product', lazy=True))
    stock = db.Column(db.Integer)
    cost = db.Column(db.Integer)
    selling_price = db.Column(db.Integer)
    orders = db.relationship('Order', secondary='opbeans_orderline')


class OrderLine(db.Model):
    __tablename__ = 'opbeans_orderline'
    product_id = db.Column(db.Integer, db.ForeignKey('opbeans_product.id'), primary_key=True)
    product = db.relationship('Product')

    order_id = db.Column(db.Integer, db.ForeignKey('opbeans_order.id'), primary_key=True)
    order = db.relationship('Order')

    amount = db.Column(db.Integer)


@app.route('/api/products')
def products():
    product_list = Product.query.order_by("id").all()
    data = []
    for p in product_list:
        data.append({
            'id': p.id,
            'sku': p.sku,
            'name': p.name,
            'stock': p.stock,
            'type_name': p.product_type.name
        })
    return jsonify(data)


@app.route('/api/products/top')
def top_products():
    sold_amount = func.sum(OrderLine.amount).label('sold')
    product_list = db.session.query(
        Product.id,
        Product.sku,
        Product.name,
        Product.stock,
        sold_amount
    ).outerjoin(OrderLine).group_by(Product.id).order_by(sold_amount.desc()).limit(3)
    return jsonify([{
        'id': p.id,
        'sku': p.sku,
        'name': p.name,
        'stock': p.stock,
        'sold': p.sold,
    } for p in product_list])


@app.route('/api/products/<int:pk>')
def product(pk):
    product = Product.query.options(joinedload(Product.product_type)).get(pk)
    if not product:
        abort(404)
    return jsonify({
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "stock": product.stock,
        "cost": product.cost,
        "selling_price": product.selling_price,
        "type_id": product.product_type_id,
        "type_name": product.product_type.name
    })


@app.route("/api/products/<int:pk>/customers")
def product_customers(pk):
    customers = Customer.query.join(Order).join(OrderLine).join(Product).filter(Product.id == pk).order_by(Customer.id).all()
    return jsonify([{
        "id": cust.id,
        "full_name": cust.full_name,
        "company_name": cust.company_name,
        "email": cust.email,
        "address": cust.address,
        "postal_code": cust.postal_code,
        "city": cust.city,
        "country": cust.country,
    } for cust in customers])


@app.route('/api/types')
def product_types():
    types_list = ProductType.query.all()
    data = []
    for t in types_list:
        data.append({
            'id': t.id,
            'name': t.name,
        })
    return jsonify(data)


@app.route('/api/types/<int:pk>')
def product_type(pk):
    product_type = ProductType.query.filter_by(id=pk)[0]
    products = Product.query.filter_by(product_type=product_type)
    return jsonify({
        "id": product_type.id,
        "name": product_type.name,
        "products": [{
            "id": product.id,
            "name": product.name,
        } for product in products]
    })


@app.route("/api/customers")
def customers():
    customers = Customer.query.all()
    data = []
    for customer in customers:
        data.append({
            "id": customer.id,
            "full_name": customer.full_name,
            "company_name": customer.company_name,
            "email": customer.email,
            "address": customer.address,
            "postal_code": customer.postal_code,
            "city": customer.city,
            "country": customer.country,
        })
    return jsonify(data)


@app.route("/api/customers/<int:pk>")
def customer(pk):
    try:
        customer_obj = Customer.query.filter_by(id=pk)[0]
    except IndexError:
        app.logger.warning('Customer with ID %s not found', pk, exc_info=True)
        abort(404)
    return jsonify({
        "id": customer_obj.id,
        "full_name": customer_obj.full_name,
        "company_name": customer_obj.company_name,
        "email": customer_obj.email,
        "address": customer_obj.address,
        "postal_code": customer_obj.postal_code,
        "city": customer_obj.city,
        "country": customer_obj.country,
    })

@app.route("/api/stats")
def stats():
    return jsonify({
        "products": Product.query.count(),
        "customers": Customer.query.count(),
        "orders": Order.query.count(),
        "numbers":{
            "revenue": 0,
            "cost": 0,
            "profit": 0,
        }
    })


@app.route('/images/<path:path>')
def image(path):
    return send_from_directory(os.path.join("opbeans", "static", "build", "images"), path)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):

    return render_template("index.html", **rum_settings())


RUM_CONFIG = None

def rum_settings():
    global RUM_CONFIG
    if RUM_CONFIG:
        return RUM_CONFIG
    url = os.environ.get('ELASTIC_APM_JS_SERVER_URL')
    if not url:
        url = apm.client.config.server_url
    package_json_file = os.path.join('opbeans', 'static', 'package.json')
    if os.path.exists(package_json_file):
        with open(package_json_file) as f:
            package_json = json.load(f)
    else:
        package_json = {}
    service_name = os.environ.get('ELASTIC_APM_JS_SERVICE_NAME', package_json.get('name', "opbeans-rum"))
    service_version = os.environ.get('ELASTIC_APM_JS_SERVICE_VERSION', package_json.get('version', None))
    RUM_CONFIG = {
        "RUM_SERVICE_NAME": service_name,
        "RUM_SERVICE_VERSION": service_version,
        "RUM_SERVER_URL": url
    }
    return RUM_CONFIG


if __name__ == '__main__':
    app.run(debug=True, port=5000)
