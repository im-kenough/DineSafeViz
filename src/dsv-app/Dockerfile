FROM python:3.14.8-alpine3.24@sha256:7f2ec713f0436c59df2362d973b6a05af9e87ba78f0e94f5245c302984a7a1fd AS build
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.14.8-alpine3.24@sha256:7f2ec713f0436c59df2362d973b6a05af9e87ba78f0e94f5245c302984a7a1fd
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN addgroup -S -g 65532 nonroot \
 && adduser -S -D -H -u 65532 -G nonroot nonroot
WORKDIR /app
COPY --from=build /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=build /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --chown=nonroot:nonroot . .
USER nonroot:nonroot
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
