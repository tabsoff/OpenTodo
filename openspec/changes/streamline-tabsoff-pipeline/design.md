# Design

## Context

See proposal.md. The official CI already splits `make check`; a second workflow repeats it. Pushes always enable all application jobs. The server has root-owned fixed-path release tooling and separate forced-command SSH keys. Production remains on the official image.

## Goals / Non-Goals

Reduce redundant runner work and manual release inputs while keeping trusted post-merge builds, owner approval, private migration rehearsal and root-owned deployment policy. Do not change application code or promote production as part of installing tooling.

## Decisions

- Keep the upstream job graph and publish gates. A small downstream classifier supplies code/docs outputs for PR and push ranges; CI changes, unknown files, tags, explicit dispatch and upstream integration use full checks. Operator-only changes run Python tests and repository checks once without creating an application image. Remove the duplicate full-check workflow.
- Use one shared Python staging guard/client entry point instead of duplicated inline YAML. Normal staging skips successful CI runs without a published-image job; manual recovery rejects them. Reuse the existing image, without a new registry publication.
- Production first reads root-owned staged state using the staging credential in a separate preparation job. It freezes image/revision and displays them before the production environment approval. Production-key promotion still validates frozen identifiers and baseline under the server lock. A newer stage causes rejection, never silent promotion of a different image.
- Add a root-only installer that installs reviewed repository code atomically, records a normalized SHA256 and keeps the previous executable. CI reads helper checksum from status and rejects mismatched controllers. Workflows cannot install root code.
- Retain at most three ordinary release snapshots, with a configurable disk budget; always protect the active rollback snapshot and displaced data. Prune only images recorded as managed by this helper, never unrelated containers/images; protect current production, staging and every retained recovery image. Treat cleanup as post-deployment housekeeping and report incomplete cleanup without invalidating a successful release.
- Run the real helper against temporary Compose projects and directories in Linux CI. Substitute only fixed host paths, Caddy/Portainer integration and registry transport; use real containers, SQLite, native restore and HTTP mutations. Use a named failed candidate entrypoint to verify automatic recovery. Never mount real app data.

## Risks / Trade-offs

- Classification could skip required jobs → conservative unknown-file handling, explicit official-update detection and regression cases; all image publications still depend on every application gate.
- A staged candidate can change while awaiting approval → freeze identifiers first and revalidate on server.
- Root helper update could diverge from workflows → checksum handshake, atomic install, retained previous helper and operator-only installation.
- Disk cleanup can affect recovery → protect all retained metadata images, active state, containers and displaced directories; no global prune or force image removal.
- Upstream workflow changes can conflict → downstream logic lives in scripts/tabsoff and necessary workflow edits are localized; preserve original build/scan/sign steps.

## Migration Plan

Create a focused branch/PR, run Python and repository checks plus disposable Docker integration. Install the reviewed helper using the root-only installer and confirm compatibility/status without modifying production. Merge after checks; operator-only changes should finish without rebuilding the app or staging a nonexistent image. Verify production preparation without executing promotion. Update the local user guide. Recovery: installer retains the prior helper; workflows can be reverted independently, and data/images remain paired.
