FROM python:3.11.9-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd --system --create-home appuser
USER appuser

EXPOSE 3001

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:3001/health', timeout=2).status == 200 else 1)" || exit 1

CMD ["python", "app.py"]
