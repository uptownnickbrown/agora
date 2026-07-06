FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml ./
COPY app ./app
COPY sim ./sim
COPY alembic.ini ./
COPY alembic ./alembic
# tests/bots.py + scripts/seed_midcourse.py power the nightly demo reset.
# They aren't installed as packages, so put the source root on the import path
# deterministically — the worker's demo_reset does `from scripts.seed_midcourse
# import main`, and `arq app.worker...` resolves `app` from site-packages, not
# /srv, so cwd alone can't be trusted to make scripts/ + tests/ importable.
ENV PYTHONPATH=/srv
COPY tests ./tests
COPY scripts ./scripts
RUN pip install --no-cache-dir .
EXPOSE 8000
# api service: this CMD. worker service overrides with: arq app.worker.WorkerSettings
# BIND_HOST=:: on Railway (private networking is IPv6-only); 0.0.0.0 locally
# (Docker port publishing and embedded DNS are IPv4). PORT is platform-injected.
CMD ["sh", "-c", "uvicorn app.main:app --host ${BIND_HOST:-0.0.0.0} --port ${PORT:-8000}"]
