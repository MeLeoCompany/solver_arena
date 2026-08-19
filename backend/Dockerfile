FROM python:3.13-slim

# curl — needed to install uv (for QORE's separate CPython 3.8 interpreter,
# ABI-incompatible with the app's own Python — see app/config.py).
# cuOpt itself needs no CUDA-flavored base image: cuopt-cu13's own pip
# dependencies (cudf-cu13, cupy-cuda13x, etc.) bundle the CUDA userspace
# libraries; only the NVIDIA driver needs to be visible at runtime, passed
# through via nvidia-container-toolkit (see docker-compose.yml).
# libgomp1 — cuDSS (cuOpt's QP barrier-method linear solver) uses a GNU
# OpenMP threading layer (libcudss_mtlayer_gomp.so.0) for the parallel
# sparse factorization; python:3.13-slim doesn't include it by default,
# and without it cuDSS segfaults on a null pointer as soon as it reaches
# that code path (reproduced on real hardware — barrier-solve crash).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libgomp1 \
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
# likely to fail, no CUDA build toolchain here) source build. Installed
# as its own explicit, pinned step (not folded into the project install
# below) so its own dependency resolution never gets pulled in a
# different direction by the web-app dependencies.
RUN pip install --no-cache-dir --extra-index-url=https://pypi.nvidia.com 'cuopt-cu13==26.8.*'

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
