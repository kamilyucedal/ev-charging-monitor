FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (Docker layer caching için)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY monitor.py .

CMD ["python", "monitor.py"]