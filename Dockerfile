FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /app/requirements.txt

COPY application /app/application

EXPOSE 8501

CMD ["streamlit", "run", "application/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
