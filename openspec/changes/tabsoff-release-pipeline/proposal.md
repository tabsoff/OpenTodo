# Proposal

## Why

Tabsoff needs a maintainable downstream OpenTodo installation: small custom changes must survive official stable updates, and experiments must not touch working task data.

## What Changes

- Keep a `tabsoff` branch based on the installed official v0.9.0 release, with independent feature pull requests.
- Reuse official CI gates and publish immutable commit images; deploy successful builds to a separate test installation.
- Provide explicit production promotion, pre-update backup, health checks and paired application/data rollback.
- Open deduplicated pull requests for official stable releases; never auto-merge or auto-update production.
- Document operation and credential recovery. No application UI, API, op log, schema or mandatory application environment variable changes.

## Capabilities

### New Capabilities

None: downstream deployment tooling only (`skip_specs: true`).

### Modified Capabilities

None. Existing self-hosting and backup/restore requirements remain unchanged.

## Impact

GitHub workflows, downstream deployment tools and operator documentation. Uses Python standard library, existing Docker/Compose, Caddy and GitHub Actions; no runtime application dependency or bundle/binary size increase. Supports ROADMAP's core small-container self-hosting goal and release hygiene. Out of scope: calendar customizations, app behavior changes, automatic conflict resolution, automatic production releases and changes to VPN/SparkyFitness.
