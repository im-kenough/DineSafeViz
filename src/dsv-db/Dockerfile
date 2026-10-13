FROM python:3.15.0rc3-alpine3.24@sha256:f288a00331ddad8ddf86aa9d83331f188d9a5b1999dea3762adf2af1968b0c04

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY refresh.py data.py ./

CMD ["python3", "refresh.py"]
