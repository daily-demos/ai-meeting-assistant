FROM python:3.12-bookworm

RUN ldd --version
COPY ./requirements.txt /app/server/requirements.txt
WORKDIR /app
RUN pip install -r server/requirements.txt
COPY . /app/server
EXPOSE 80

CMD quart --app server/main.py run --host=0.0.0.0 --port 80
