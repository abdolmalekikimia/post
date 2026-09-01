# Integration Automation Portfolio

This repository is a portfolio-safe example of Python integration testing for
device-oriented services. It demonstrates REST and SignalR clients, reusable
service wrappers, response assertions, positive and negative flows, stress
scenarios, and structured execution reports.

## Important privacy note

This repository is intentionally sanitized for public portfolio use.

- Internal ticket and issue identifiers were replaced with descriptive names
  such as `history_backend`, `delivery_merge`, and `destination_update`.
- Internal service names, business terminology, document references, and
  environment-specific wording were replaced with neutral industry language.
- Internal hostnames, IP addresses, URLs, credentials, device identifiers, and
  tokens were replaced with safe placeholders such as
  `api.example.invalid`, `0.0.0.0`, `demo-device`, and `demo-token`.
- Endpoint and message names were generalized while preserving the client,
  flow, assertion, and reporting architecture.
- The original organized layout was kept so the repository demonstrates the
  engineering approach without exposing company-specific implementation
  details.

The examples are not connected to a real service. Configure a local mock or
demo server before running end-to-end scenarios.

## Project layout

```text
config/       environment-backed settings
clients/      REST and SignalR transport clients
services/     reusable service wrappers
flows/        lifecycle, synchronization, upload, routing, and container flows
assertions/   response-contract assertions
tests/unit/   isolated unit tests
tests/success/positive integration flows
tests/negative/negative scenario flows
tests/stress/ volume and concurrency scenarios
docs/         public-facing scenario notes
postman/      generic Postman examples
utils/        logging, test data, stress helpers, and reports
```

## Setup

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config/test.env.example config/test.env
```

Set `BASE_URL` and `WS_URL` to a local mock or demo service. The checked-in
examples use the reserved `example.invalid` domain and do not contain live
credentials.

## Test groups

Unit tests run without a service:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit -q
```

Positive, negative, and stress flows are disabled by default. Enable only the
flow you want to run with its corresponding environment flag, for example:

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success -q -s
```

Stress scenarios support configurable iteration counts, delays, fail-fast
behavior, and concurrent operations. Reports include step status, request
payload, response, expectation, and error information; sensitive values are
redacted by default.
