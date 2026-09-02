# Scenario Catalog

This catalog summarizes the additional scenario coverage represented in the
latest local development work. The public names below are intentionally
descriptive and do not expose internal ticket identifiers.

## Configuration and device lifecycle

- Configuration synchronization and healthy device authentication
- Invalid synchronization snapshots and policy validation
- Administrative authentication, device authentication, handshake, and
  connection-lifecycle negative paths

## Inbound and lookup integrations

- Upstream history responses with success, rejection, timeout, unavailable,
  and discrepancy outcomes
- Delivery merge and destination lookup polling outcomes
- Deferred image and supplementary-data upload responses
- Status mapping and override validation

## Destination operations

- Destination assignment with and without an optional chute
- Destination updates, repeated assignments, state preservation, and
  post-container-close rejection

## Container and packing contracts

- Container selection filters and invalid selection inputs
- Export-before-container negative paths
- Container response contracts, counters, error items, and container identity
- Physical container audit response validation

The executable public suites for these areas are under `tests/success`,
`tests/negative`, and `tests/stress`. Their flows remain layered through
`flows/`, `services/`, `clients/`, and `assertions/`; this document is only a
portfolio-oriented index and does not claim access to a production system.
