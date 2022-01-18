import os
import json

from flask import Flask, jsonify, abort, render_template, send_from_directory
from flask_migrate import Migrate

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

apm = ElasticAPM(app)

#tracing = FlaskTracing(opentracing_tracer, trace_all_requests=True, app=app)


if "GRAPHQL_URL" not in os.environ:
    from sql_implementation.models import db
    from sql_implementation import sql

    migrate = Migrate(app, db)

    db.init_app(app)
    app.config["sqldb"] = db

    app.register_blueprint(sql)

if "GRAPHQL_URL" in os.environ:
    from gql import Client
    from gql.transport.requests import RequestsHTTPTransport
    from gql_implementation import gql_imp

    client = Client(
        transport=RequestsHTTPTransport(
            url=os.environ["GRAPHQL_URL"],
            retries=3,
        ),
        fetch_schema_from_transport=True,
    )
    app.config["gql_client"] = client
    app.register_blueprint(gql_imp)




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
