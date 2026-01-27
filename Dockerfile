FROM python:3.9-slim

WORKDIR /app

# Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Code
COPY . .

# Run Gunicorn
# Bind to 0.0.0.0:$PORT (Railway Requirement)
# Default PORT is 8000 if not set
CMD sh -c "gunicorn app:app --bind 0.0.0.0:${PORT:-8000}"
