# VajraTwin backend — FastAPI + physics/ML digital twin.
# Local-first, no cloud SDKs.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

EXPOSE 8000

# MONGODB_URI is injected via environment (compose). If Mongo is unreachable,
# the app automatically falls back to in-memory demo mode and still runs.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
