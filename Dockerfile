# Stage 1: Build Stage
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies if needed (e.g., for psycopg2 or bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install python dependencies into a local folder
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final Runtime Stage
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Install runtime dependencies and wget for Cloud SQL Proxy in Cloud Build
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 wget ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /install /usr/local

# Copy the application code
COPY . .

# Create a non-root user for security during production (Cloud Run)
RUN addgroup --system appgroup && adduser --system --group appuser
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose the port (informative only)
EXPOSE 8080

# Use exec form for faster signal handling
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]