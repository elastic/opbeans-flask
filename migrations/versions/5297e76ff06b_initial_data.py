"""initial data

Revision ID: 5297e76ff06b
Revises: e157ee29908d
Create Date: 2019-12-13 12:50:34.230207

"""
import os
import subprocess
from alembic import op
import json
from dateutil import parser as dateutil_parser
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = '5297e76ff06b'
down_revision = 'e157ee29908d'
branch_labels = None
depends_on = None

customers_table = table('opbeans_flask_customer',
    column('id', sa.Integer),
    column("full_name", sa.String(1000)),
    column("company_name", sa.String(1000)),
    column("email", sa.String(1000)),
    column("address", sa.String(1000)),
    column("postal_code", sa.String(1000)),
    column("city", sa.String(1000)),
    column("country", sa.String(1000)),
)

orders_table = table("opbeans_flask_order",
    column("id", sa.Integer),
    column("customer_id", sa.Integer),
    column("created_at", sa.DateTime),
)

product_types_table = table("opbeans_flask_producttype",
    column("id", sa.Integer),
    column("name", sa.String(1000)),
)

products_table = table("opbeans_flask_product",
    column("id", sa.Integer),
    column("sku", sa.String(1000)),
    column("name", sa.String(1000)),
    column("description", sa.Text),
    column("product_type_id", sa.Integer),
    column("stock", sa.Integer),
    column("cost", sa.Integer),
    column("selling_price", sa.Integer),
)
                       
order_lines_table = table("opbeans_flask_orderline",
    column("product_id", sa.Integer,),
    column("order_id", sa.Integer),
    column("amount", sa.Integer),
)


def upgrade():
    bulks = {
        "order": (orders_table, []),
        "customer": (customers_table, []),
        "product": (products_table, []),
        "producttype": (product_types_table, []),
        "orderline": (order_lines_table, []),
    }
    renames = {
        "order": "order_id",
        "customer": "customer_id",
        "product_type": "product_type_id",
        "product": "product_id",
    }
    file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "initial_data.json")
    subprocess.check_call(["bunzip2", "-k", file + ".bz2"])
    with open(file) as f:
        data = json.load(f)
    for item in data:
        key = item["model"].split(".")[1]
        fields = {"id": item["pk"]}
        fields.update(item["fields"])
        for rename, to in renames.items():
            if rename in fields:
                fields[to] = fields.pop(rename)
        if "created_at" in fields:
            fields["created_at"] = dateutil_parser.parse(fields["created_at"])
        bulks[key][1].append(fields)
    for _, (t, items) in bulks.items():
        op.bulk_insert(t, items)

    os.unlink(file)


def downgrade():
    pass
