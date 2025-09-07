#!/bin/sh
set -e

# пытаемся скачать модели
if python -m utils.voice.download_models_script; then
  echo "[entrypoint] models ok"
else
  echo "[entrypoint] models download failed or skipped, continuing..." >&2
fi

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"