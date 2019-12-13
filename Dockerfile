FROM python:3.8

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements*.in /app/
RUN /app/venv/bin/pip install -U pip pip-tools && \
    /app/venv/bin/pip-compile requirements.in && \
    /app/venv/bin/pip install -r requirements.txt

FROM python:3.8-slim

RUN apt-get -qq update \
 && apt-get -qq install -y \
    bzip2 \
    curl \
	--no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

WORKDIR app

ADD . /app
RUN mkdir /app/venv
ENV PATH=/app/venv/bin:$PATH

COPY --from=0 /app/venv /app/venv
COPY --from=opbeans/opbeans-frontend:latest /app/build /app/opbeans/static/build
## To get the client name/version from package.json
COPY --from=opbeans/opbeans-frontend:latest /app/package.json /app/opbeans/static/package.json

RUN sed 's/<head>/<head>{% block head %}{% endblock %}/' /app/opbeans/static/build/index.html | sed 's/<script type="text\/javascript" src="\/rum-config.js"><\/script>//' > /app/templates/base.html

# init demo database
RUN mkdir -p /app/demo \
    && DATABASE_URL="sqlite:////app/demo/db.sql" ELASTIC_APM_DISABLE_SEND=true ELASTIC_APM_CENTRAL_CONFIG=false flask db upgrade

EXPOSE 3000

CMD ["honcho", "start", "--no-prefix"]
