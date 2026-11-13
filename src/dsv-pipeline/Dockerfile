FROM python:3.14.10-alpine3.24@sha256:5862d971d1f0ae26b258cefa4e893556b1d3aba81bd2ff30888704ad378bab67

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
