FROM python:3.15.2-alpine3.24@sha256:0f9552bb28711333da16915ec146f5e6bb44a7fdac9ced15dc17c2e0206346dd
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN addgroup -S -g 65532 nonroot \
 && adduser -S -D -H -u 65532 -G nonroot nonroot
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Security remediation: pip isn't used at runtime, and the packages it
# vendors (urllib3, msgpack, setuptools) carried HIGH CVEs in image scans.
RUN python -m pip uninstall -y pip
COPY --chown=nonroot:nonroot . .
USER nonroot:nonroot
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
