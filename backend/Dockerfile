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
# mypy — only for its stubgen, used by the "загрузить новый .so для QORE"
# admin feature (app/services/qore_versions/) to regenerate qore_opt_py.pyi
# after a swap; stubgen has to import the compiled module to introspect it,
# so it must run under this same interpreter, not the app's own 3.13 one.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && uv python install 3.8 \
    && uv pip install --python "$(uv python find 3.8)" --break-system-packages mypy

WORKDIR /app

# Set to "false" (docker-compose.yml's base file defaults it that way) to
# skip cuOpt/CUDA entirely on a box with no GPU — multi-GB RAPIDS download
# for nothing, since CPLEX/ALGLIB/QORE don't need any of it and already
# degrade cuOpt to "unavailable" gracefully via the existing availability
# check when the import fails. docker-compose.gpu.yml flips this to "true".
ARG INSTALL_CUOPT=false

# cuopt-cu13's own transitive deps (e.g. libcuopt-cu13) are hosted on
# NVIDIA's package index, not plain PyPI — without --extra-index-url pip
# either can't find a wheel at all or falls back to a very slow (and
# likely to fail, no CUDA build toolchain here) source build. Installed
# as its own explicit, pinned step (not folded into the project install
# below) so its own dependency resolution never gets pulled in a
# different direction by the web-app dependencies.
# Placed BEFORE any COPY of app code/metadata so this heavy CUDA layer
# stays cached across ordinary code changes — it depends on nothing here.
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$INSTALL_CUOPT" = "true" ]; then \
        pip install --extra-index-url=https://pypi.nvidia.com 'cuopt-cu13==26.8.*'; \
    else \
        echo "INSTALL_CUOPT=false — skipping cuOpt/CUDA deps, cuOpt will show as unavailable"; \
    fi

# Project metadata first, so the dependency install below only re-runs
# when pyproject.toml changes — not on every source edit.
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip pip install .

# App code copied last: edits here invalidate nothing above.
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY engines ./engines

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]