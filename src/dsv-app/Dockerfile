FROM python:3.15.0rc3-alpine3.24@sha256:f288a00331ddad8ddf86aa9d83331f188d9a5b1999dea3762adf2af1968b0c04 AS build
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.15.0rc3-alpine3.24@sha256:f288a00331ddad8ddf86aa9d83331f188d9a5b1999dea3762adf2af1968b0c04
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN addgroup -S -g 65532 nonroot \
 && adduser -S -D -H -u 65532 -G nonroot nonroot
WORKDIR /app
COPY --from=build /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=build /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --chown=nonroot:nonroot . .
USER nonroot:nonroot
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
