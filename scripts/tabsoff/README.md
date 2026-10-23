# Tabsoff OpenTodo operations

This directory is downstream operator tooling, outside the application runtime.

## Everyday changes

Start with the agreed [local-preview development workflow](DEVELOPMENT.md). The [Russian user guide](USER-GUIDE.md) covers preview, review, staging and release. These documents contain no credentials.

1. Branch from `tabsoff`, iterate locally with separate synthetic data, and show the result to the user. Open a pull request back to `tabsoff` after the user approves the local result; do not publish every intermediate edit or create a PR for each preview iteration.
2. Merge after CI is green. Application changes pass the original upstream tests/build/security gates and publish `ghcr.io/tabsoff/opentodo:sha-<full-commit>`. Operator-only edits run Python/repository tests and a disposable deployment lifecycle check, without rebuilding the application. Documentation changes run documentation checks; unknown inputs, CI edits, release tags, manual full CI and official release integration run the full suite. Pushes are classified against their before/after commits, not merely their event type.
3. **Tabsoff staging** resolves that tag to an immutable digest, privately rehearses production database migrations without networking, and updates <https://todo-test.tabsoff.ru>. Its data lives in `/opt/opentodo-test/data`, separate from `/opt/opentodo/data`. Use synthetic tasks there. The initial test owner is created separately; its browser login and local offline storage are independent of production.
4. Verify the feature on test.
5. Open **Actions → Tabsoff production → Run workflow**, choose `tabsoff` and `promote`. The preparation job freezes the current tested digest and source revision and displays them in the run summary before the production environment approval. Review and approve. Only that frozen, previously staged candidate can be promoted; a changed staging candidate or production baseline rejects the request. Production stays on <https://todo.tabsoff.ru>.

Release images are pinned by digest. Use the release workflows for updates; manual image changes invalidate the staged baseline. Portainer remains useful for status and logs. The helper keeps its saved stack source consistent with `/opt/opentodo/docker-compose.yml`.

If an automatic staging attempt fails because of runner/SSH transport, run **Tabsoff staging** manually from `tabsoff` with the full source SHA. Automatic and manual staging share the same controller. It requires a successful trusted `tabsoff` push CI run whose image publication job succeeded. Operator-only CI runs have no image publication and are skipped automatically; manual staging rejects them. Existing images are reused without rebuilding/publishing. Staging and production mutations share a GitHub concurrency group plus the server lock, which waits up to 60 seconds for other deployments or backups.

The duplicate **Tabsoff deployment checks** and separate **Tabsoff retry staging** workflows are removed. Full application checks still run on both a PR and its merged result; they validate potentially different trees.

## Official updates

**Tabsoff official updates** runs daily or manually and opens one `upstream/vX.Y.Z` PR for the newest stable release. It integrates the release with the downstream branch without rebasing or resetting your custom commits. A clean integration explicitly dispatches CI (GitHub bot-created PRs do not trigger normal PR events). Conflicts remain visible and must be resolved before checks/merge. Review the changelog and CI, merge, verify staging, then promote manually. Never auto-merge upstream updates.

## Restore and failure recovery

Promotion briefly puts production in maintenance mode, stops it, saves its full data directory and exact old Compose/image, then starts the tested image. A failed health check automatically restores the paired old image and data. Rollback invokes OpenTodo's official restore command so its sync generation rotates and devices reseed. It preserves the displaced directory for recovery.

For a later deliberate rollback, run **Tabsoff production** with `rollback`; image/revision inputs are ignored. This returns server data to the **pre-update snapshot**, including undoing subsequent server-side changes. Offline/pending operations can sync again afterward. Inspect important post-update changes before rollback; displaced files remain under the snapshot for recovery. Do not simply run an older image against a migrated database.

Snapshots: `/var/backups/opentodo-releases/<UTC timestamp>/` (root only). By default keep up to three ordinary snapshots within a 1 GiB release-snapshot budget. Always protect the currently recorded rollback snapshot and every directory containing displaced data, even when this exceeds the budget. An optional root-owned `/var/lib/opentodo-release/retention.json` accepts `{"snapshots":3,"max_bytes":1073741824}`. A budget-exceeded flag is reported for operator review. Existing daily backups remain independent. Disk headroom is checked before changes.

After staging/promotion, cleanup can remove only unused digest references recorded by this helper in `managed-images.json`. Current production/staging images, staged baselines, every retained snapshot image and all container image IDs are protected. Images predating the inventory are untouched. No global prune or force removal is used. A cleanup failure is reported without changing a successful release into a failed deployment.

After a killed/interrupted deployment, `/var/lib/opentodo-release/pending.json` blocks further writes. The operator inspects its snapshot and maintenance state. With the server stopped, restore the full snapshot and then invoke the paired old image's official restore command using `restore.tar.gz`; restore `compose.json`, synchronize Portainer's stack source, start and check health, then clear the pending marker and maintenance snippet. Do not clear the marker merely to retry a newer release. The root helper's `restore(Path(snapshot))` function provides this same recovery path from an operator-owned Python session.

## Installation and credentials

From a reviewed checkout on the server, run `sudo python3 scripts/tabsoff/install.py`. The root-only installer normalizes line endings, validates Python syntax, takes the deployment/backup locks, refuses unfinished deployments and atomically installs `/usr/local/sbin/opentodo-release` (root-owned, mode 0755). The prior executable remains at `/usr/local/sbin/opentodo-release.previous`; repeated installation of the same content does not overwrite that recovery copy. Its checksum is recorded in `/var/lib/opentodo-release/helper-install.json` and reported by `status`.

The CI client compares that checksum with its checked-out `release.py` before any mutation. If they differ, install the reviewed helper first. Workflows and restricted SSH keys cannot install root code. An old queued controller fails safely after a helper update. The installer updates tooling only, without changing application containers or data. If needed, an operator can restore the previous executable under the same locks and revert the corresponding workflow change.

The existing Caddy site, separate data/Compose directories, Portainer stacks and restricted SSH/sudo policy must already be provisioned as described below; this installer updates the helper, not an entire new VPS. `/etc/caddy/opentodo-release.caddy` is imported inside the production site block; normally it removes the maintenance header, and returns 503 during maintenance. Test uses loopback port 8081 and a separate Caddy login; production uses 8080.

Create Linux user `opentodo-deploy` with no password and two dedicated SSH keys. Each authorized key uses `restrict,command="sudo -n /usr/local/sbin/opentodo-release --stage-only"` or `--production-only`; sudo permits exactly these two command/argument combinations. Each receives bounded JSON on stdin. The staging key cannot promote or roll back production; the production key cannot select untested images. No shell, forwarding or arbitrary image registry is allowed.

GitHub configuration:

- Default branch `tabsoff`; allow Actions to create PRs.
- Environment secrets named `OPENTODO_DEPLOY_KEY`: separate private keys in `staging` and `production` (never commit them or set a repository-wide fallback).
- Repository variable `OPENTODO_DEPLOY_KNOWN_HOSTS`: operator-verified SSH host key for 89.223.70.53.
- Environments `staging` and `production`; production requires the owner to review and only permits the `tabsoff` branch. Self-review is allowed for a single-person installation.
- Environment `maintenance`, restricted to `tabsoff`, stores `UPSTREAM_PUSH_KEY`: a dedicated write-enabled deploy key for this repository alone. It permits upstream changes to workflow files without a broad personal token. Variable `UPSTREAM_KNOWN_HOSTS` pins GitHub's SSH host key obtained from its official HTTPS metadata API. This key has no server access.
- Registry credentials use each workflow's short-lived `GITHUB_TOKEN`; the server uses a temporary Docker login and removes it after pulling. Application data and backups never leave the VPS.

Verify helper tests with `python3 -m unittest discover -s scripts/tabsoff -p 'test_*.py' -v`. On a Linux Docker host, run `sudo python3 scripts/tabsoff/lifecycle_smoke.py [local-candidate-image]`: it uses unique temporary Compose projects, loopback-only random ports and synthetic owner/tasks; it verifies actual promotion, native paired rollback and automatic failed-container recovery, including restored task data and rotated sync generation. Host Caddy/Portainer are substituted and host images are never pruned. It never mounts production/test data. CI passes the application image built/scanned in that same run via a short-lived artifact; operator-only changes use the pinned baseline without rebuilding the app. Publication waits for this test. Keep root recovery access independent of the workflow key. For key rotation, replace the restricted authorized key and GitHub secret together.
