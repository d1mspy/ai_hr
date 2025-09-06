ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=10 \
    PIP_PROGRESS_BAR=off

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      aria2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/

RUN mkdir -p /wheels \
 && aria2c -o /wheels/torch.whl -x 16 -s 16 -k 1M --retry-wait=5 --max-tries=20 \
      "https://download.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl" \
   || true

RUN --mount=type=cache,target=/root/.cache/pip \
    ( [ -f /wheels/torch.whl ] && pip wheel --no-deps /wheels/torch.whl -w /wheels || true )

RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --prefer-binary -r requirements/ml.txt     -w /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --prefer-binary -r requirements/docs.txt   -w /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --prefer-binary -r requirements/base.txt   -w /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --prefer-binary -r requirements/server.txt -w /wheels

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

RUN python -m venv /venv

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements/ requirements/

RUN pip install --no-index --find-links=/wheels -r requirements/ml.txt \
 && pip install --no-index --find-links=/wheels -r requirements/docs.txt \
 && pip install --no-index --find-links=/wheels -r requirements/base.txt \
 && pip install --no-index --find-links=/wheels -r requirements/server.txt

RUN adduser --disabled-password --gecos '' appuser
USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 8000
ENV PORT=8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]