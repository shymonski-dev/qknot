# syntax=docker/dockerfile:1

FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QKNOT_SERVE_FRONTEND=1

COPY backend/requirements.txt ./backend/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r ./backend/requirements.txt

COPY backend ./backend
COPY dist ./dist

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
