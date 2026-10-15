# Inference API for APS workshop triage.
# Build after the final evaluation: the image needs the frozen model and decision file.
FROM python:3.13.7-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-service.txt .
RUN pip install --no-cache-dir -r requirements-service.txt
COPY src/ src/
COPY artifacts/model/ artifacts/model/
COPY reports/final/execution.json reports/final/execution.json
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "aps_intel.service:app", "--host", "0.0.0.0", "--port", "8000"]
