# Task 01: Backend Unit Tests (Python/pytest)

## Context
HillsRun backend has 33 Python files, 3500+ lines of code, 100+ database methods, 10 API routers — and zero tests. The `pyproject.toml` lists pytest as a dev dependency but no `tests/` directory exists. This is the highest-priority improvement for codebase stability.

## Scope
Add comprehensive pytest test suite covering:
- Pure utility functions (token_manager, config parsing, retry logic)
- Database query methods (with mocked asyncpg pool)
- API routers (with FastAPI TestClient)
- Fetcher transformations (data normalization)

## Implementation Details

### Files to Create
- `tests/conftest.py` — Shared fixtures (mock DB, mock Garmin client, test config)
- `tests/test_token_manager.py` — Fernet encrypt/decrypt, key generation
- `tests/test_config.py` — Config from env, from dict, validation
- `tests/test_database.py` — Query methods with mocked asyncpg
- `tests/test_routers/test_health.py` — Health endpoint
- `tests/test_routers/test_daily.py` — Daily summary, sleep, stress, HR, body battery
- `tests/test_routers/test_activities.py` — Activity list, detail, splits, update
- `tests/test_routers/test_sync.py` — Sync trigger, job tracking
- `tests/test_fetchers/test_transforms.py` — Data transformation logic (pure functions)
- `tests/test_garmin_client.py` — Rate limiting, retry logic

### Key Functionality
- Test pure functions first (highest ROI, no mocks needed)
- Mock asyncpg.Pool for database tests
- Use FastAPI TestClient for router integration tests
- Mock garminconnect library for fetcher tests

### Technologies Used
- pytest + pytest-asyncio (async test support)
- unittest.mock / pytest-mock
- FastAPI TestClient (httpx-based)

## Success Criteria
- [ ] `pytest tests/` passes with 0 failures
- [ ] >50 test cases covering core logic
- [ ] Token encryption/decryption round-trip verified
- [ ] All 10 router endpoints have at least one test
- [ ] Fetcher data transformations tested with realistic payloads

## Dependencies
**Must complete first**: None (standalone)
**Blocks**: Task 05 (CI/CD)

## Related Documentation
- **ARCHITECTURE.md**: Backend section
- **docs/SCHEMA.md**: Database structure

---
**Estimated Time**: 3 hours
**Phase**: Foundation
