[![Build Status](https://apm-ci.elastic.co/job/apm-agent-python/job/opbeans-flask-mbp/job/master/badge/icon)](https://apm-ci.elastic.co/job/apm-agent-python/job/opbeans-flask-mbp/job/master/)

# Opbeans for Ponies

This is an implementation of the [Opbeans Demo app](http://opbeans.com) in Django. It uses the same
database schema as the [Node](https://github.com/opbeat/opbeans) version.

The database settings are provided via environment variable, like so:

    DATABASE_URL=postgres://user:password@host:port/dbname ./manage.py runserver

## Installation

**Note**: We highly recommend to use Python 3.5+

Create a `virtualenv` with your preferred tooling, then install the requirements:

    python -m pip install -r requirements.txt

If you want to use Celery, you'll also need to set up a Redis instance.
The easiest way for local development is via docker:

    docker run -p 6379:6379 redis


## Demo Data

There's a compressed SQLite database in the `demo` directory. You can run it like this:

    bunzip2 -k demo/db.sql.bz2
    ./manage.py collectstatic
    DATABASE_URL=sqlite://./demo/db.sql ./manage.py runserver

There's an admin user, `barista`/`affogato`.

## Testing locally

The simplest way to test this demo is by running:

```bash
make test
```

Tests are written using [bats](https://github.com/sstephenson/bats) under the tests dir

## Publishing to dockerhub locally

Publish the docker image with

```bash
    VERSION=1.2.3 make publish
```

NOTE: VERSION refers to the tag for the docker image which will be published in the registry
