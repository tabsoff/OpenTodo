# Pipeline optimization decisions — 2026-10-22

Agreed priorities from the operator review:

1. Remove duplicate full application checks. Keep one set per source revision, and recheck the merged tree.
2. Classify tooling, documentation and application inputs. Preserve full checks for unknown inputs, workflow edits and official release integration; avoid `[skip ci]` as routine practice.
3. Promote the current tested candidate without copying a digest/revision by hand. Freeze and display it before owner approval, then revalidate it on the server.
4. Keep downstream logic separate to reduce upstream merge conflicts. Share manual and automatic staging; preserve upstream build/scan/sign gates.
5. Test a complete real deployment/rollback cycle on disposable synthetic data, including failed-candidate automatic recovery.
6. Make helper updates reproducible and detectable, and bound storage growth while protecting recovery data and images.

Implementation and operating details: [README.md](README.md). Delivery and verification tracking: `openspec/changes/streamline-tabsoff-pipeline/tasks.md`.

Deliberate boundaries: no automatic production promotion, no global Docker pruning, no new application dependencies, no product/calendar behavior changes. Production data is never used in public/synthetic test environments. The upstream separate image-test and multi-architecture publication builds are retained to avoid expanding this change into a redesign of its release system.
