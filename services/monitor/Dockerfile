FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.9 \
    kafka-python==2.0.2 \
    elasticsearch==8.11.0

COPY monitor.py .

CMD ["python", "monitor.py"]