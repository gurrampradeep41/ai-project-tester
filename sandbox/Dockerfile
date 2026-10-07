FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system appuser \
    && useradd \
        --system \
        --gid appuser \
        --create-home \
        --home-dir /home/appuser \
        appuser

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip \
    && pip install \
        --no-cache-dir \
        -r /app/requirements.txt

COPY . /app

RUN rm -rf \
    /app/.git \
    /app/.pytest_cache \
    /app/__pycache__ \
    /app/core/__pycache__ \
    /app/.env \
    /app/.env.local \
    /app/.env.production \
    2>/dev/null || true

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=20s \
    --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]