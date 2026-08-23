# Stage 1: Build the React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY member3/frontend/package*.json ./
RUN npm install
COPY member3/frontend ./
RUN npm run build

# Stage 2: Python FastAPI Runtime
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend dist from stage 1
COPY --from=frontend-builder /app/frontend/dist /app/member3/frontend/dist

# Expose port (default 8000)
ENV PORT=8000
EXPOSE 8000

# Start FastAPI server
CMD ["sh", "-c", "uvicorn member3.backend.main:app --host 0.0.0.0 --port ${PORT}"]
