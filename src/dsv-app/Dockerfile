FROM python:3.14.9-alpine3.24@sha256:dbeb11d16bb95c3a7e3c25c842cb9f20cbc8c18f8be0461a4a0dcc861ad386a0 AS build
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.14.9-alpine3.24@sha256:dbeb11d16bb95c3a7e3c25c842cb9f20cbc8c18f8be0461a4a0dcc861ad386a0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN addgroup -S -g 65532 nonroot \
 && adduser -S -D -H -u 65532 -G nonroot nonroot
WORKDIR /app
COPY --from=build /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=build /usr/local/bin/gunicorn /usr/local/bin/gunicorn
# Security remediation: pip isn't used at runtime, and the packages it
# vendors (urllib3, msgpack, setuptools) carried HIGH CVEs in image scans.
RUN python -m pip uninstall -y pip
COPY --chown=nonroot:nonroot . .
USER nonroot:nonroot
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
