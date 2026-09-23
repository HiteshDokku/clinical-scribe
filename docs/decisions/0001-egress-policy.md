# ADR-0001: Egress policy — "egress-denied, LAN-isolated," not "air-gapped"

**Status:** accepted
**Date:** 2026-09-20
**Owner:** Krishna Patil

## Context

The original FF-180 synopsis simultaneously promises an "air-gapped" Docker
architecture and an EHR Integration Gateway that pushes finalized notes over
a network. These two claims cannot both be literally true, and an examiner
will notice the contradiction.

## Decision

Drop "air-gapped." The `clinic` Docker network is defined with
`internal: true` (see `docker-compose.yml`), meaning no container on it has
a default route to the internet. The single exception is
`services/fhir-gateway`, which additionally joins a second `edge` network
and is restricted, both at the application layer (an explicit host:port
allowlist read from `FHIR_ALLOWLIST_HOST`/`PORT`) and at the host firewall
in production (`infra/firewall/`), to exactly one destination.

This is enforced, not just documented:
`tests/security/test_no_egress.py` asserts that the asr, llm, and safety
containers cannot open a socket to any public host, and
`tests/fhir/test_egress_allowlist.py` asserts the fhir-gateway refuses any
host other than the allowlisted one.

## Consequences

- The privacy claim ("no PHI leaves the machine") is verifiable by a test
  suite run in CI, not just asserted in a report.
- The FHIR gateway is a deliberately narrow, auditable exception, which is
  a stronger and more honest story than a blanket "no network access"
  claim that the architecture doesn't actually support.
- Every new service must be explicitly placed on `clinic` only, unless it
  has a documented, allowlisted reason to also join `edge`.

## Alternatives considered

- **True air-gap (no EHR push at all):** rejected — it would mean cutting
  the EHR Integration Gateway objective entirely, which is core to the
  synopsis's value proposition.
- **VPN tunnel from every service:** rejected — needlessly complex, and
  widens the attack surface compared to a single narrow egress point.
