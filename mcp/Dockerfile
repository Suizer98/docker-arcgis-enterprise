FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 arcgisuser && chown -R arcgisuser:arcgisuser /app
USER arcgisuser

EXPOSE 8001

CMD ["python", "main.py"]
