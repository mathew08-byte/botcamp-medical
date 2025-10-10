# Integration Tests

Use docker-compose Postgres and Redis for integration tests.

Suggested env:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/botcamp_test
```

Run:
```
pytest -q tests/integration
```
