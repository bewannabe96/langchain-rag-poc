FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY langchain_rag/ langchain_rag/
COPY streamlit_app.py .

EXPOSE 9012

CMD ["sh", "-c", "streamlit run streamlit_app.py --server.port 9012"]