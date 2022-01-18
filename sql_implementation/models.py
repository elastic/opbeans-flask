import datetime
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Customer(db.Model):
    __tablename__ = 'opbeans_flask_customer'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(1000))
    company_name = db.Column(db.String(1000))
    email = db.Column(db.String(1000))
    address = db.Column(db.String(1000))
    postal_code = db.Column(db.String(1000))
    city = db.Column(db.String(1000))
    country = db.Column(db.String(1000))


class Order(db.Model):
    __tablename__ = 'opbeans_flask_order'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('opbeans_flask_customer.id'), nullable=False)
    customer = db.relationship('Customer', backref=db.backref("opbeans_order", lazy=True))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    products = db.relationship('Product', secondary='opbeans_flask_orderline')


class ProductType(db.Model):
    __tablename__ = 'opbeans_flask_producttype'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000), unique=True)

    def __str__(self):
        return self.name


class Product(db.Model):
    __tablename__ = 'opbeans_flask_product'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(1000), unique=True)
    name = db.Column(db.String(1000))
    description = db.Column(db.Text)
    product_type_id = db.Column('product_type_id', db.Integer, db.ForeignKey('opbeans_flask_producttype.id'), nullable=False)
    product_type = db.relationship('ProductType', backref=db.backref('opbeans_flask_product', lazy=True))
    stock = db.Column(db.Integer)
    cost = db.Column(db.Integer)
    selling_price = db.Column(db.Integer)
    orders = db.relationship('Order', secondary='opbeans_flask_orderline')


class OrderLine(db.Model):
    __tablename__ = 'opbeans_flask_orderline'
    product_id = db.Column(db.Integer, db.ForeignKey('opbeans_flask_product.id'), primary_key=True)
    product = db.relationship('Product')

    order_id = db.Column(db.Integer, db.ForeignKey('opbeans_flask_order.id'), primary_key=True)
    order = db.relationship('Order')

    amount = db.Column(db.Integer)