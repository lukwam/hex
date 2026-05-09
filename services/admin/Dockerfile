FROM python:3.12-slim

WORKDIR /app

COPY services/admin/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared/ /app/services/shared/
COPY services/admin/ /app/services/admin/

ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "services.admin:app"]
