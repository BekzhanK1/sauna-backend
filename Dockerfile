# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
  && apt-get install -y build-essential libpq-dev curl netcat-openbsd gcc \
  && rm -rf /var/lib/apt/lists/*


# Install pipenv or requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run Django app
CMD ["gunicorn", "sauna.wsgi:application", "--bind", "0.0.0.0:8000"]
