This folder is reserved for automated tests for the T16BGPTless project.

Suggested structure:

- `tests/backend/` – tests for the Flask API (e.g. using pytest).
- `tests/frontend/` – tests for the React frontend (e.g. using Vitest/Testing Library).
- `tests/gptless_tests/` - tests for blackbox testing the api from the client's perspective.

## Black-box client tests (`tests/gptless_tests/`)

- Integration tests against the real deployed API.
- Tests require `API_TOKEN` and `API_BASE_URL` to be set; otherwise they are skipped (to avoid accidental real HTTP calls in CI/local).
