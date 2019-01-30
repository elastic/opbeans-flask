import datetime
import os

import requests

from flask import Flask, jsonify, abort
from flask_sqlalchemy import SQLAlchemy

import opentracing
from flask_opentracing import FlaskTracing

from sqlalchemy.sql import func
from elasticapm.contrib.flask import ElasticAPM
from elasticapm.contrib.opentracing import Tracer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SQLITE_DB_PATH = 'sqlite:///' + os.path.abspath(os.path.join(BASE_DIR, 'demo', 'db.sql'))

DJANGO_API_URL = os.environ.get("DJANGO_API_URL", "http://localhost:8000")

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
opentracing_tracer = Tracer(config={"SERVICE_NAME": "opbeans-flask-ot"})


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', SQLITE_DB_PATH)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ELASTIC_APM'] = {
    'SERVICE_NAME': os.environ.get('ELASTIC_APM_SERVICE_NAME', 'opbeans-flask'),
    'SERVER_URL': os.environ.get('ELASTIC_APM_SERVER_URL', 'http://localhost:8200'),
    'DEBUG': True,
}
db = SQLAlchemy(app)
apm = ElasticAPM(app, logging=True)

#tracing = FlaskTracing(opentracing_tracer, trace_all_requests=True, app=app)


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(1000))
    company_name = db.Column(db.String(1000))
    email = db.Column(db.String(1000))
    address = db.Column(db.String(1000))
    postal_code = db.Column(db.String(1000))
    city = db.Column(db.String(1000))
    country = db.Column(db.String(1000))


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    customer = db.relationship('Customer', backref=db.backref('orders', lazy=True))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    products = db.relationship('Product', secondary='order_lines')


class ProductType(db.Model):
    __tablename__ = 'product_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000), unique=True)

    def __str__(self):
        return self.name


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(1000), unique=True)
    name = db.Column(db.String(1000))
    description = db.Column(db.Text)
    product_type_id = db.Column('type_id', db.Integer, db.ForeignKey('product_types.id'), nullable=False)
    product_type = db.relationship('ProductType', backref=db.backref('products', lazy=True))
    stock = db.Column(db.Integer)
    cost = db.Column(db.Integer)
    selling_price = db.Column(db.Integer)
    orders = db.relationship('Order', secondary='order_lines')


class OrderLine(db.Model):
    __tablename__ = 'order_lines'
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), primary_key=True)
    product = db.relationship('Product')

    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), primary_key=True)
    order = db.relationship('Order')

    amount = db.Column(db.Integer)


@app.route('/api/products')
def products():
    product_list = Product.query.all()
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
    product_list = db.session.query(
        Product.id,
        Product.sku,
        Product.name,
        Product.stock,
        func.sum(OrderLine.amount).label('sold')
    ).join(OrderLine).group_by(Product.id).order_by('-sold').limit(3)
    return jsonify([{
        'id': p.id,
        'sku': p.sku,
        'name': p.name,
        'stock': p.stock,
        'sold': p.sold,
    } for p in product_list])


@app.route('/api/products/<int:pk>')
def product(pk):
    result = requests.get(DJANGO_API_URL + "/api/products/{}".format(pk))
    return jsonify(result.json())


@app.route("/api/products/<int:pk>/customers")
def product_customers(pk):
    result = requests.get(DJANGO_API_URL + "/api/products/{}/customers".format(pk))
    return jsonify(result.json())


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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
