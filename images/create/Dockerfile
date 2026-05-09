FROM python:3.12.8-slim

COPY . /app

RUN pip install -r /app/requirements.txt

WORKDIR /app

CMD ["python", "app.py"]
