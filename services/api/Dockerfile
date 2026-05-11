FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared/ /app/services/shared/
COPY services/api/ /app/services/api/

ENV PYTHONPATH=/app
EXPOSE 8081

CMD ["uvicorn", "services.api:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "2"]
