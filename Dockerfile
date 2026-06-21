FROM python:3.11-slim

WORKDIR /app

ARG PIP_NO_CACHE=0
COPY backend/requirements.txt .
RUN if [ "$PIP_NO_CACHE" = "1" ]; then pip install --no-cache-dir -r requirements.txt; else pip install -r requirements.txt; fi

COPY backend/ /app/

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
