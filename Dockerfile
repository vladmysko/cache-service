FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY cli ./cli

RUN pip install --no-cache-dir .

RUN mkdir -p /data

ENV DATABASE_URL=sqlite:////data/cache.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]