FROM python:3.11.9-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd --system --create-home appuser
USER appuser

EXPOSE 3001

# Client timeout must exceed /health's worst-case (B probe 0.5s). Exit 137 +
# "failed container health checks" on ECS was caused by /health taking ~2s
# while this client timed out at 2s.
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:3001/health', timeout=4).status == 200 else 1)" || exit 1

CMD ["python", "app.py"]
