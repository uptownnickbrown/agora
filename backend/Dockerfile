FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml ./
COPY app ./app
COPY sim ./sim
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-cache-dir .
EXPOSE 8000
# api service: this CMD. worker service overrides with: arq app.worker.WorkerSettings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
