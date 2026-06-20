FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv==0.5.11

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev || uv sync

COPY app ./app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
