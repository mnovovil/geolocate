# Run the geolocate CLI in a container. Build from the repo root:
#   docker build -f docker/Dockerfile -t geolocate .
# Usage: see Quick start in README.md; mounts, config and --user: see docs/reference.md.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/geolocate \
    GEOLOCATE_CONFIG=/config/.geolocate.json

RUN useradd --create-home --home-dir /home/geolocate --uid 1000 geolocate

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Bake the DuckDB extensions into the image so runs need network only for S3. They're
# installed for the DuckDB version just pip-installed, and made readable for any --user UID.
RUN python -c "import duckdb; c = duckdb.connect(); c.install_extension('spatial'); c.install_extension('httpfs')" \
    && chmod -R a+rX /home/geolocate

# Only the code: .geolocate.json may hold credentials and is mounted at runtime instead.
COPY src/ /app/src/

USER geolocate
WORKDIR /data
ENTRYPOINT ["python", "/app/src/geolocate.py"]
