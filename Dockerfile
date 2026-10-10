FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MADAR_DB_PATH=/app/var/madar.sqlite3
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home madar
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY workflows/ ./workflows/
COPY --from=frontend /build/dist/ ./frontend/dist/
RUN mkdir -p var && chown -R madar:madar /app
USER madar
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=4)"
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
