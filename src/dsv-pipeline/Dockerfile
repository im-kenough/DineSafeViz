FROM python:3.15.0-alpine3.24@sha256:2699b90f4d562a22e2dd076c82f964032f64814204bff36d271a54ba4cc2c7e2

RUN addgroup -S -g 65532 nonroot \
 && adduser -S -D -H -u 65532 -G nonroot nonroot

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Security remediation: pip isn't used at runtime, and the packages it
# vendors (urllib3, msgpack, setuptools) carried HIGH CVEs in image scans.
RUN python -m pip uninstall -y pip

COPY --chown=nonroot:nonroot dinesafe_csv.py loader.py data.py pipeline.py ./

USER nonroot:nonroot
# scripts/pipeline.sh passes the subcommand: ingest, load, or run.
ENTRYPOINT ["python3", "pipeline.py"]
CMD ["--help"]
