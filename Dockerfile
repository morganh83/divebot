FROM python:3.9.16-alpine3.17

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /requirements.txt

RUN python3 -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /requirements.txt

RUN mkdir /app
WORKDIR /app
COPY . /app

CMD ["/py/bin/python3", "divebot.py"]