FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
ARG INSTALL_OPTIONAL_CONNECTORS=true
COPY requirements.txt requirements-connectors.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "${INSTALL_OPTIONAL_CONNECTORS}" = "true" ]; then \
      pip install --no-cache-dir -r requirements-connectors.txt; \
    fi
COPY app ./app

RUN useradd --create-home --uid 10001 osiel && \
    mkdir -p /app/data && chown -R osiel:osiel /app
USER osiel

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
