FROM python:3.14-slim-bookworm AS build
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 65532 nonroot \
 && useradd --uid 65532 --gid 65532 --no-create-home nonroot
WORKDIR /app
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --from=build /usr/local/bin/flask /usr/local/bin/flask
COPY --chown=nonroot:nonroot . .
USER nonroot:nonroot
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
