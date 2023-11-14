FROM python:3.12-bookworm

RUN ldd --version

# copy the requirements file into the image
COPY ./requirements.txt /app/server/requirements.txt

# switch working directory
WORKDIR /app

# install the dependencies and packages in the requirements file
RUN pip install -r server/requirements.txt

# copy every content from the local file to the image
COPY . /app/server

EXPOSE 80

CMD quart --app server/main.py --debug run --host=0.0.0.0 --port 80
