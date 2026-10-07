# Cache Service

A FastAPI microservice that transforms two lists of strings, interleaves the results, and stores both transformations and generated payloads in SQLite or PostgreSQL. A CLI sends requests to the service using Pydantic Settings for argument parsing and validation.

## Run locally

Requires Python 3.10 or newer. Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive API documentation is available at `/docs`, and `GET /health` returns `{"status":"ok"}`.

Database tables are created automatically at startup. By default, the database is `cache.db` in the current working directory. Set `DATABASE_URL` in the environment or a `.env` file to change its location:

```bash
DATABASE_URL=sqlite:////tmp/cache-service.db uvicorn app.main:app
```

## Run with Docker

Requires Docker with Docker Compose:

```bash
docker compose up --build -d
docker compose logs -f api
```

The API is exposed on port 8000. SQLite data is stored in `/data/cache.db` inside the container, backed by the named `cache-data` volume. Stop the service with `docker compose down`; the volume and cached data remain available for the next start.

## Choose a database

SQLite is the default and needs no separate server. To use PostgreSQL locally, set an explicit SQLAlchemy URL with the included Psycopg driver:

```bash
DATABASE_URL='postgresql+psycopg://cache:cache@localhost:5433/cache' uvicorn app.main:app --reload
```

The database must already exist; application tables are created automatically. Switching URLs selects a different database and does not migrate existing cached data.

An alternative, standalone Compose configuration starts the API and PostgreSQL together:

```bash
docker compose -f docker-compose.postgres.yml up --build -d
```

Stop the SQLite Compose service first if it is using port 8000. The API waits for PostgreSQL's health check before starting. PostgreSQL data persists in the `postgres-data` volume, and the database is accessible locally on port 5433. The example credentials `cache:cache` are for local development; configure separate credentials for deployment.

```bash
docker compose -f docker-compose.postgres.yml logs -f api
docker compose -f docker-compose.postgres.yml down
```

## API example

Create a payload:

```bash
curl -X POST http://127.0.0.1:8000/payload \
  -H 'Content-Type: application/json' \
  -d '{"list_1":["first string","second string","third string"],"list_2":["other string","another string","last string"]}'
```

The response has HTTP status `201` and contains a generated identifier:

```json
{"id": "<payload-id>"}
```

Use that identifier to retrieve the result:

```bash
curl http://127.0.0.1:8000/payload/<payload-id>
```

```json
{
  "output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
}
```

Both input fields must be lists of strings with equal lengths. Empty lists produce an empty output string. Invalid input returns `422`; an unknown payload identifier returns `404`. Repeated creation requests return `201` even when an existing identifier is reused.

## CLI

Installing the project makes the `cache-cli` command available. Keep the server running and use another terminal with the virtual environment activated:

```bash
cache-cli --help
cache-cli --json '{"list_1":["hello"],"list_2":["world"]}'
cache-cli --host http://127.0.0.1:8000 --repeat 3 \
  --json '{"list_1":["hello"],"list_2":["world"]}'
```

| Argument | Short form | Meaning | Default |
| --- | --- | --- | --- |
| `--host URL` | `-H` | Server URL | `http://127.0.0.1:8000` |
| `--repeat N` | `-r` | Number of sequential POST requests, at least 1 | `1` |
| `--input FILE` | `-i` | Read JSON from a file; `-` reads stdin | Unset |
| `--json JSON` | `-j` | Read JSON from an argument | Unset |
| `--output FILE` | `-o` | Write results to a file; `-` writes stdout | `-` |
| `--help` | `-h` | Show help | — |

Provide exactly one of `--input` and `--json`. The task assigns `-h` to both host and help; this implementation uses uppercase `-H` for host to avoid that conflict. Argument names are case-sensitive.

Read from a file and write the responses to another file:

```bash
echo '{"list_1":["hello"],"list_2":["world"]}' > request.json
cache-cli -i request.json -r 3 -o responses.jsonl
```

Read from stdin:

```bash
printf '%s\n' '{"list_1":["hello"],"list_2":["world"]}' | cache-cli -i -
```

Each successful iteration produces one JSON object containing the payload ID. Multiple responses use newline-delimited JSON. The CLI sends POST requests only; retrieve the actual output with the GET endpoint. Results are written after all iterations succeed. File, input, and HTTP errors are reported on stderr with exit status `1`; HTTP requests have a 30-second timeout.

The CLI is also included in the Docker image, so it can call the API from the running container:

```bash
docker compose exec api cache-cli -j '{"list_1":["hello"],"list_2":["world"]}'
```

## Design and caching

The request flows through API schemas, a payload service, and database repositories. The transformer currently calls `str.upper()` to simulate an external service.

- A request-local dictionary avoids repeated lookups for duplicate strings within one request.
- The `transform_cache` table stores transformations keyed by the exact input string and reuses them across requests and restarts.
- The `payload` table stores UUID identifiers, complete output strings, and SHA-256 fingerprints of those outputs. Inputs producing the same output reuse the existing payload ID. Looking up the output also preserves IDs created by earlier versions with input-based fingerprints.
- Transformations and payload creation share a transaction. A failure rolls back the changes.

SQLite uses `BEGIN IMMEDIATE` before reading the cache to serialize generation across connections and processes. This prevents concurrent requests from transforming the same uncached input or inserting conflicting records. PostgreSQL uses a transaction advisory lock for the same purpose. Reads through the GET endpoint do not acquire this generation lock.

## Tests

With the development dependencies installed:

```bash
python -m pytest -q
python -m pytest --cov=app --cov=cli --cov-report=term-missing
```

To run the same suite against PostgreSQL, start the database and provide its URL:

```bash
docker compose -f docker-compose.postgres.yml up -d --wait db
TEST_DATABASE_URL='postgresql+psycopg://cache:cache@localhost:5433/cache' python -m pytest -q
```

Tests create and remove a unique schema for each test; the database user needs permission to create schemas. Existing application tables are left untouched. Without `TEST_DATABASE_URL`, tests use temporary SQLite files.

Unit tests cover interleaving, ID reuse, transformer call counts, rollback, and CLI input/output and HTTP behavior. Integration tests cover the API and concurrent service calls using separate database connections.

## Scope and tradeoffs

SQLite is the default database; PostgreSQL can be selected through `DATABASE_URL`. The PostgreSQL driver is included in the application dependencies.

Generation requests, including cache hits, run sequentially under a database lock. This favors correctness and avoiding duplicate transformer calls over throughput. Long-running transformations or sustained contention can exceed SQLite's lock timeout; this approach is intended for the small service in this task.

Payloads are stored as database strings and returned as JSON. The service has no cache expiration or eviction, and assumes the transformer remains deterministic and unchanged. Changing transformation behavior would require a cache invalidation strategy. Tables are created at startup without a migration framework. Dependencies are currently unpinned.
