# API do Meu Guardião (FastAPI). O front vai para a Vercel; este container vai para
# qualquer host que rode Docker (Render, Railway, Fly...).
FROM python:3.12-slim

WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY motor_dor ./motor_dor
COPY api ./api
COPY db ./db

ENV PYTHONUNBUFFERED=1
# O host injeta PORT; 8000 é o padrão local.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
