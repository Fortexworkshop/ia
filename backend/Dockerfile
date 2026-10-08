# Image du backend FORTEX. Contexte de build : racine du depot ia.
#   docker build -f backend/Dockerfile -t fortex-backend .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Le backend reutilise seulement la configuration de sentinel/ (aucune dependance IA)
COPY sentinel/__init__.py sentinel/config.py sentinel/sensors.py sentinel/
COPY presence/__init__.py presence/config.py presence/
COPY backend/ backend/
COPY scripts/backend.py scripts/backend.py

# Durcissement : utilisateur sans privileges
RUN useradd --system --uid 10001 --no-create-home fortex
USER fortex

EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
CMD ["python", "scripts/backend.py", "--host", "0.0.0.0", "--port", "8080"]
