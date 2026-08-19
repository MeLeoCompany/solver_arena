FROM python:3.13-slim

# curl — needed to install uv (for QORE's separate CPython 3.8 interpreter,
# ABI-incompatible with the app's own Python — see app/config.py).
# cuOpt itself needs no CUDA-flavored base image: cuopt-cu13's own pip
# dependencies (cudf-cu13, cupy-cuda13x, etc.) bundle the CUDA userspace
# libraries; only the NVIDIA driver needs to be visible at runtime, passed
# through via nvidia-container-toolkit (see docker-compose.yml).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && uv python install 3.8

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY engines ./engines

# cuopt-cu13's own transitive deps (e.g. libcuopt-cu13) are hosted on
# NVIDIA's package index, not plain PyPI — without --extra-index-url pip
# either can't find a wheel at all or falls back to a very slow (and
# likely to fail, no CUDA build toolchain here) source build.
RUN pip install --no-cache-dir --extra-index-url=https://pypi.nvidia.com .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
