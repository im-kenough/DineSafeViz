FROM python:3.14.8-alpine3.24@sha256:7f2ec713f0436c59df2362d973b6a05af9e87ba78f0e94f5245c302984a7a1fd

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY refresh.py data.py ./

CMD ["python3", "refresh.py"]
