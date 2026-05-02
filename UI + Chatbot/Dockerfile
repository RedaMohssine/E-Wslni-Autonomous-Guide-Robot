FROM python:3.11-slim

WORKDIR /app

# 1. Install dependencies first (best caching)
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy project AFTER dependencies
COPY . /app

# 3. Streamlit port
EXPOSE 8501

# 4. Start Streamlit
CMD ["sh", "-c", "streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]