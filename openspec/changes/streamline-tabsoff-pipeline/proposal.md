# Proposal

## Why

The downstream release pipeline repeats application checks for operator-only edits and requires copying image identifiers to promote a tested build. Simplify routine maintenance while keeping isolated staging, owner approval, immutable images and paired database/image recovery.

## What Changes

- Run operator tests once in CI; classify documentation, downstream tooling and application changes. Unknown inputs and CI edits fail toward the full suite. Official release integration receives full checks.
- Share automatic/manual staging implementation and validate successful source CI plus a published image before deployment.
- Resolve the staged candidate before production approval, show its identifiers and promote exactly that frozen candidate without manual copying.
- Add a disposable Docker integration test exercising successful promotion, explicit rollback and failed-candidate automatic recovery with synthetic tasks through the real API.
- Provide a root-only reproducible helper installer, helper checksum compatibility checks and scoped retention for snapshots/images protecting recovery state.
- Document priorities, operating instructions and verified results.

## Capabilities

### New Capabilities

None. Downstream operator tooling only (`skip_specs: true`).

### Modified Capabilities

None. Application behavior, sync protocol, schema and upstream release safety requirements remain unchanged.

## Impact

GitHub Actions, scripts/tabsoff and operator documentation. No application dependencies, mandatory application environment variables, image-size or runtime-memory change. Supports release hygiene; no product ROADMAP feature. Out of scope: product/calendar changes, automatic production promotion, removing upstream security gates, changing VPS networking or migrating production data.
