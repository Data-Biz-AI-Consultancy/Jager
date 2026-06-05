FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY src/ml/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY src/ml/*.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
