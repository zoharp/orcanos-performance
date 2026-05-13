# ---- Stage 1: Build React frontend ----
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend + Playwright ----
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Chromium browser and install its OS-level dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

COPY backend/ ./backend/
COPY --from=frontend-builder /frontend/dist ./frontend/dist

RUN mkdir -p /data/scenarios

EXPOSE 8080

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8080"]
