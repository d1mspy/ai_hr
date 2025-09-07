ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=900 \
    PIP_RETRIES=10 \
    PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      aria2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/

COPY third_party/torch-2.8.0+cpu-cp312-cp312-manylinux_2_28_x86_64.whl /wheels/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --prefer-binary -r requirements/torch_local.txt     -w /wheels
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

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
COPY requirements/ requirements/

RUN pip install --no-index --find-links=/wheels torch==2.8.0 \
 && pip install --no-index --find-links=/wheels -r requirements/ml.txt \
 && pip install --no-index --find-links=/wheels -r requirements/docs.txt \
 && pip install --no-index --find-links=/wheels -r requirements/base.txt \
 && pip install --no-index --find-links=/wheels -r requirements/server.txt

RUN adduser --disabled-password --gecos '' appuser \
 && mkdir -p /models \
 && chown -R appuser:appuser /models

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
 && chmod 0755 /usr/local/bin/docker-entrypoint.sh

USER appuser
COPY --chown=appuser:appuser . .

EXPOSE 8000
ENV PORT=8000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]