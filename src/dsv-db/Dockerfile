FROM python:3.15.0rc1-slim-trixie

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY refresh.py .

CMD ["python3", "refresh.py"]
