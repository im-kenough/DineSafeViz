FROM python:3.14.9-alpine3.24@sha256:dbeb11d16bb95c3a7e3c25c842cb9f20cbc8c18f8be0461a4a0dcc861ad386a0

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
