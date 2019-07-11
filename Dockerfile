FROM python:3.7

WORKDIR /app

COPY requirements*.txt /app/
RUN pip install -r requirements.txt

ADD . /app

RUN bunzip2 /app/demo/db.sql.bz2

COPY --from=opbeans/opbeans-frontend:latest /app/build /app/opbeans/static/build

RUN mkdir -p /app/opbeans/templates
RUN cp /app/opbeans/static/build/index.html /app/opbeans/templates/

EXPOSE 3000

CMD ["honcho", "start"]
