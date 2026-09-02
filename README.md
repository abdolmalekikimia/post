# Integration Automation Portfolio

This repository is a sanitized portfolio representation of a Python QA/SDET
integration-testing project for device-oriented services. It demonstrates
REST and SignalR/WebSocket clients, reusable service wrappers, layered flows,
response-contract assertions, positive and negative scenarios, stress helpers,
and structured execution reports.

It is not connected to a production system. End-to-end scenarios require a
local mock or demo service configured with the example environment values.

## Important privacy note

This public version was prepared specifically for portfolio use:

- Internal company names, ticket/issue identifiers, service names, document
  references, and business-specific wording were replaced with neutral
  terminology.
- Real hostnames, IP addresses, URLs, credentials, tokens, device identifiers,
  and environment-specific values were replaced with safe placeholders such as
  `api.example.invalid`, `0.0.0.0`, `demo-device`, and `demo-token`.
- Scenario and flow names were made descriptive without relying on internal
  tracking numbers.
- The existing project layout and testing architecture were preserved so the
  engineering approach remains visible without exposing private systems.

Before publishing any future change, review both the working tree and Git
history for newly introduced secrets or organization-specific identifiers.

## Architecture

```text
Test
  ↓
Flow
  ↓
Service
  ↓
Client
  ↓
REST / SignalR-WebSocket
  ↓
Response
  ↓
Assertion
  ↓
Execution Report
```

- **Test** selects a scenario and controls its environment.
- **Flow** orchestrates a business-neutral sequence of operations.
- **Service** exposes reusable domain-facing operations.
- **Client** owns REST or SignalR/WebSocket transport details.
- **Response** captures status, payload, and protocol results.
- **Assertion** validates response contracts and expected outcomes.
- **Execution Report** records steps, payloads, responses, expectations, and
  errors with sensitive values redacted by default.

## Project layout

```text
config/       environment-backed settings and mock-service examples
clients/      REST and SignalR/WebSocket transport clients
services/     reusable service wrappers
flows/        lifecycle, synchronization, routing, upload, and container flows
assertions/   response-contract assertions
tests/unit/   isolated unit tests
tests/success/positive integration flows
tests/negative/negative scenario flows
tests/stress/ volume and concurrency scenarios
docs/         public-facing scenario and configuration notes
              (see `docs/scenarios/README.md` for the generic scenario catalog)
postman/      generic Postman examples
utils/        logging, test data, stress helpers, and reporting
```

## Configuration

Install dependencies and create a local environment file:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config/test.env.example config/test.env
```

Set `BASE_URL` and `WS_URL` in the ignored `config/test.env` to a local mock or
demo service. `config/backend-mock.env.example` documents generic mock
fixtures and contains no production connection details. Never commit a local
`.env` file or real credentials.

## Test execution

The default pytest configuration excludes stress tests and marks end-to-end
tests as skipped unless explicitly enabled.

Unit tests:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit -q
```

Positive/integration scenarios:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success -q -s
```

Negative scenarios:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/negative -q -s
```

Stress scenarios:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/stress -q -s -o addopts=""
```

The integration and stress commands assume that the corresponding local mock
or demo service and fixtures are available. Scenario-specific environment
flags are documented in `config/test.env.example` and the related files under
`docs/`.

## Reporting

Execution helpers produce structured step information, including operation
status, request payload, response, expectation, and error details. Reports
are intended for local review and are ignored by Git along with logs, Allure
output, coverage files, and other generated artifacts.

## Public sanitization

The repository intentionally preserves the shape of an organized automation
codebase while removing identifying implementation details. Generic terms such
as “REST client”, “SignalR/WebSocket client”, “gateway”, and “mock service” are
used only to describe the testing techniques represented here; they do not
claim access to any real production endpoint.
