# metaproject-zeus-collector
Metaproject Zeus's Collector module for collecting various data from various sources and sending them in uniform format to main module of Metaproject Zeus

## Prerequisites
- Python 3.13
- Poetry ≥ 1.8

## Setup
```bash
poetry install
cp .env.example .env
```

## Local run
```bash
poetry run python -m collector.main
```

## Docker
```bash
docker compose up --build
```
