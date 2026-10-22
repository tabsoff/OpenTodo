# Design

## Context

Production runs official v0.9.0 on a 1 GB VPS alongside other services. See proposal.md for motivation. The fork must preserve upstream CI and avoid building on the VPS.

## Goals / Non-Goals

**Goals:** one tested image digest promoted from test to production; separate persistent test data; no automatic production changes; safe restore across SQLite migrations.

**Non-Goals:** a general deployment platform, schema or sync changes, production data in public previews.

## Decisions

- Extend the existing CI branch allow-list and add full commit SHA image tags. Preserve upstream gates, signing and attestations instead of maintaining a second application build.
- A successful trusted `tabsoff` push triggers staging through a restricted SSH key. A separate key, available only in the owner-reviewed production environment, promotes the staged digest. The staging key cannot change production. SSH accepts bounded JSON, fixed actions and only this fork's digest-qualified image. No shell or general Docker access is granted.
- A root-owned Python standard-library helper is installed separately by the operator. GitHub cannot replace it. GitHub registry credentials are ephemeral and passed through SSH stdin. Operator deployment secrets stay outside Git.
- Public test uses its own directory and database. A private disposable SQLite backup of production is started with `--network none` to exercise migrations without exposing data or sending notifications. Success records the current production image as the candidate baseline; production promotion rejects a stale baseline.
- Promotion enters maintenance mode, stops production, saves the full data directory and image/Compose metadata, changes the image and checks health. Failure restores both. Restore invokes the official CLI on a native-format database archive so the sync generation changes and offline clients reseed correctly. Portainer's stored Compose is synchronized with the canonical file.
- Stable update detection opens a PR from the upstream release commit into `tabsoff`. Git's three-way merge preserves local changes and exposes conflicts. No moving production tags, automated production rollout or force reset.
- Deployment operations share a file lock. Keep bounded backups and explicit recovery directories; reject updates when disk headroom is insufficient. No application dependencies or bundle/binary size impact; the test instance adds one small Go server. All test execution/builds use existing GitHub runners.

## Risks / Trade-offs

- [Schema rollback] Restore the paired data snapshot using the paired old image, never run an old binary on migrated data.
- [Edits after a successful release] A later manual rollback returns server data to the snapshot; pending/offline clients may re-upload newer operations. Keep the displaced data for recovery and explain this in the runbook.
- [Root helper] Treat it as privileged operator infrastructure; validate inputs and fail closed, test rejection paths and restores with synthetic data before enabling promotion.
- [Fork workflow permissions] GitHub may prevent bot-created PRs or package publishing; configure repository permissions explicitly and verify actual runs.
- [Disk/RAM] Build off-server, retain only recent release snapshots, monitor resources; never prune unrelated containers or images.

## Migration Plan

Install staging with the already deployed official digest and separate synthetic data behind HTTPS. Install the helper, restricted key and workflows. Validate configuration and recovery using synthetic data, run upstream CI, then let successful custom builds reach staging. Production remains on its current official digest until an explicit manual promotion after review.
