from flask import Blueprint, abort, jsonify, current_app
from sqlalchemy.orm import joinedload

from sqlalchemy.sql import func

from .models import Product, ProductType, Customer, Order, OrderLine

sql = Blueprint('sql', __name__)

@sql.route('/api/products')
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


@sql.route('/api/products/top')
def top_products():
    db = current_app.config["sqldb"]
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


@sql.route('/api/products/<int:pk>')
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


@sql.route("/api/products/<int:pk>/customers")
def product_customers(pk):
    customers = Customer.query.join(Order).join(OrderLine).join(Product).filter(Product.id == pk).order_by(
        Customer.id).all()
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


@sql.route('/api/types')
def product_types():
    types_list = ProductType.query.all()
    data = []
    for t in types_list:
        data.append({
            'id': t.id,
            'name': t.name,
        })
    return jsonify(data)


@sql.route('/api/types/<int:pk>')
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


@sql.route("/api/customers")
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


@sql.route("/api/customers/<int:pk>")
def customer(pk):
    try:
        customer_obj = Customer.query.filter_by(id=pk)[0]
    except IndexError:
        current_app.logger.warning('Customer with ID %s not found', pk, exc_info=True)
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


@sql.route("/api/stats")
def stats():
    return jsonify({
        "products": Product.query.count(),
        "customers": Customer.query.count(),
        "orders": Order.query.count(),
        "numbers": {
            "revenue": 0,
            "cost": 0,
            "profit": 0,
        }
    })