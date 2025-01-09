FROM python:3.12-slim

WORKDIR /app

RUN pip install gunicorn

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY langchain_rag/ langchain_rag/
COPY app.py .

CMD ["gunicorn", "--bind=0.0.0.0:8000", "app:app"]