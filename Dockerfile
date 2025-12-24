# Use official lightweight Python image
FROM python:3.13-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements file first (to cache dependencies)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Cloud Run expects the app to listen on the PORT environment variable (default 8080)
ENV PORT=8080

# Command to run the application using Uvicorn
# "main:app" refers to file main.py, object app
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT