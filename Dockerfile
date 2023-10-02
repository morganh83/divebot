FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

RUN mkdir app
# Copy the current directory contents into the container at /app
ADD . /app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "divebot.py"]
