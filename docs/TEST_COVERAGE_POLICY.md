# Test Coverage Policy

Each scenario family is considered across three axes:

- **Positive**: healthy path and successful response contract.
- **Negative**: invalid input, expected business rejection, or error response.
- **Stress**: volume, repetition, concurrency, race, retry, or endurance.

## Statuses

- `Implemented`: executable coverage exists.
- `Missing`: the coverage is not represented by an executable test yet.
- `Planned`: the need is identified but execution is not enabled.
- `External dependency`: execution requires a local mock, fixture, restart, or
  external evidence such as logs or a database.
- `Not applicable`: an independent stress axis is not useful for the current
  contract.

Missing positive or stress coverage should not be filled with artificial tests.
The contract and risk must be understood first.

## Protocol labels

Scenario metadata may use `API`, `SignalR`, `WebSocket`, or `Mixed`. The label
helps select the appropriate client, service, fixture, and test type while
keeping the flow architecture independent of internal domain names.

## Stress readiness

Before enabling stress execution, define iterations, workers, timeout limits,
expected failure rate, race/duplicate policy, and cleanup strategy. Stress
tests remain excluded from the default run until their local fixtures are
ready.
