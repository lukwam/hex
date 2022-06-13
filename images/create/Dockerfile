FROM python:3.10-slim

COPY . /app

RUN pip install -r /app/requirements.txt

WORKDIR /app

CMD ["python", "app.py"]
