FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.7.1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      git \
      osm2pgsql \
      osmcoastline \
      gdal-bin \
      libpq-dev \
      curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app
RUN chmod +x scripts/*.sh

ENV PATH="/app/bin:${PATH}"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
