FROM python:3.14.8-alpine3.24@sha256:f6a589d43c42b9e7f7dc67a12d37132491f362859a5d750607710cc56da3bc72

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
