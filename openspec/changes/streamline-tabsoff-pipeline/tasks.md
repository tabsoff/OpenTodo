# Tasks

- [ ] 1. Consolidate checks and classify inputs conservatively; verify Python classification tests, repository path/gate checks and CI job selections for operator-only changes.
- [x] 2. Share staging validation and freeze/display the candidate before production approval; verify CI guard, client checksum and stale-candidate tests.
- [x] 3. Add reproducible root helper installation, version reporting and scoped retention; verify installer idempotence and retention protection tests.
- [x] 4. Exercise successful promotion, explicit rollback and automatic failed-candidate recovery against disposable real containers with synthetic task API writes; verify restored task data and rotated sync generation.
- [ ] 5. Document and deliver the changes through a checked PR; install the helper and verify production remains unchanged, CI succeeds and no operator-only image is published. Record equivalent full-check results from CI and update user instructions.
