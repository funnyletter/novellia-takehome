FROM python:3.14-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first so this layer is cached until pyproject.toml/uv.lock change.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev

# The data file is read relative to /app (see DEFAULT_DATA_FILE in api.py).
COPY assignment ./assignment

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Bind to 0.0.0.0 so the port is reachable from outside the container.
CMD ["uvicorn", "novellia_takehome.api:app", "--host", "0.0.0.0", "--port", "8000"]
