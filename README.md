# Invoice Generation API – T16BGPTless

An API that generates standardised UBL invoices. Clients register to obtain an API token, then create and manage invoices. Invoices can be generated from scratch (with JSON payloads) or from stored templates, and are returned as UBL 2 XML.

---

## How the system works

### Auth and API tokens

- **Registration** is gated by a developer token (see [Local development](#local-development)). With a valid developer token, you call the auth API with a `groupName` and receive an **APItoken**.
- That **APItoken** is used for all invoice operations: pass it in the `APItoken` header. Each group has its own token; you can **reset** (issue a new token) or **revoke** (invalidate the current one).

### Invoices

- **Generate**: Create an invoice by sending either `InvoiceData` (supplier, customer, lines, totals) or a `templateInvoice` ID (optionally plus overrides). The API validates the data, builds UBL XML, stores the invoice, and returns the XML.
- **List**: GET returns the IDs of the current group’s non-deleted invoices.
- **Get**: GET by ID returns the stored UBL XML for an invoice you own.
- **Delete**: Soft-delete only — the row is marked deleted and no longer appears in list/get, but is not removed from the database.

### Data and storage

- **Backend**: Python 3 with Flask. **Database**: Supabase (PostgreSQL). Tables include `api_groups` (group name, API token) and `api_invoices` (owner, template_id, xml, invoice_data, deleted flag).
- **Invoice format**: UBL 2 (OASIS). The service validates required fields and totals, then produces XML with the correct namespaces.
- **Templates**: Any stored invoice can be used as a template. When generating from a template, the template’s `invoice_data` is merged with request `InvoiceData` (request overrides). You must own the template.

---

## How to use

### Run the API locally

```bash
# From the repo root
pip install -r requirements.txt
# Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and VALID_DEV_TOKENS (see below)
python -m app.app
# Or: flask --app app.app run
```

By default the app serves on the usual Flask port. `GET /` redirects to the API documentation.

### API documentation

Open **[https://docs.gptless.au](https://docs.gptless.au)** for full API specs (routes, request/response shapes, and examples).

### Typical flow

1. **Register a group** (requires a valid developer token in `APIdevToken` header):
   - `POST /v1/auth/register` with body `{"groupName": "my-app"}`.
   - Response includes `APItoken`; store it and use it for invoice calls.
   - For the users of the API this is automatically done by filling out the startup form at https://go.gptless.au/form which will automatically call our server, generate the token and email it out to them.

2. **(optional) convert an order into invoice data**:
   - `POST /v1/orders/convert` with header `APItoken: <your-token>` and body with a raw order XML (Content-Type: application/xml or text/xml).
   - Response is `200` with the required JSON `InvoiceData` to generate an invoice.

3. **Create an invoice**:
   - `POST /v1/invoices/generate` with header `APItoken: <your-token>` and body with `InvoiceData` and/or `templateInvoice` as needed.
   - Response is `201` with UBL XML in the body.

4. **List / fetch / soft-delete**:
   - `GET /v1/invoices` — list your invoice IDs.
   - `GET /v1/invoices/<id>` — get UBL XML for one invoice.
   - `DELETE /v1/invoices/<id>` — soft-delete an invoice.

---

## Local development

### Environment variables

Create a `.env` file in the project root (do not commit secrets).

| Variable | Purpose |
|----------|---------|
| `VALID_DEV_TOKENS` | Comma-separated developer tokens that can call `/v1/auth/register`, `/v1/auth/reset`, `/v1/auth/revoke`. If unset or empty, those endpoints return **403**. |
| `SUPABASE_URL` | Supabase project URL (e.g. from `supabase status` or dashboard). |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key for backend access. |

For CI, set `VALID_DEV_TOKENS` as a GitHub Actions secret; the workflow passes it into the test run.

### Database (Supabase)

- Migrations live under `supabase/migrations/`. Apply them with the Supabase CLI (e.g. `supabase db reset` or your deployment process).
- CI starts local Supabase, runs pgTAP tests from `supabase/tests/`, then runs the Python test suite against that instance.

### Running tests

```bash
# Backend tests (set VALID_DEV_TOKENS so auth tests run; set Supabase vars if running integration tests)
export VALID_DEV_TOKENS=your-dev-token
PYTHONPATH=. pytest tests/backend -v

# With coverage
PYTHONPATH=. coverage run -m pytest tests/backend -v
coverage report -m

# Lint
pylint app/**/*.py --errors-only
```

Tests that need a real Supabase (e.g. `test_supabase.py` integration tests) require `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. Auth-related tests need `VALID_DEV_TOKENS` or they are skipped.

---

## Project layout

| Path | Description |
|------|-------------|
| `app/app.py` | Flask app, blueprint registration, home redirect. |
| `app/routes/auth.py` | Register, reset, revoke (group + API token). |
| `app/routes/invoices.py` | Generate, list, get, delete invoices. |
| `app/routes/helpers.py` | Shared helpers (DB, errors, dev-token validation). |
| `app/services/invoice_xml.py` | UBL invoice build and validation. |
| `app/db/supabase_client.py` | Supabase client singleton. |
| `supabase/migrations/` | SQL migrations for `api_groups`, `api_invoices`, RLS. |
| `supabase/tests/` | pgTAP database tests. |
| `tests/backend/` | Pytest tests (auth, invoices, helpers, XML, app). |
| `.github/workflows/ci.yml` | CI: Supabase CLI, db tests, pytest + coverage, pylint. |

---

## Tech stack

- **API**: Python 3, Flask.
- **Database**: Supabase (PostgreSQL, PostgREST).
- **Invoice format**: UBL 2 XML.
- **CI**: GitHub Actions — Supabase CLI, pgTAP, pytest, coverage, Pylint.
