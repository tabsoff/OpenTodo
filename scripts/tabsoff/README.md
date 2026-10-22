# Tabsoff OpenTodo operations

This directory is downstream operator tooling, outside the application runtime.

## Everyday changes

1. Branch from `tabsoff`, make one focused customization and open a pull request back to `tabsoff`.
2. Merge after CI is green. The original upstream tests/build/security gates publish `ghcr.io/tabsoff/opentodo:sha-<full-commit>`.
3. **Tabsoff staging** resolves that tag to an immutable digest, privately rehearses production database migrations without networking, and updates <https://todo-test.tabsoff.ru>. Its data lives in `/opt/opentodo-test/data`, separate from `/opt/opentodo/data`. Use synthetic tasks there. The initial test owner is created separately; its browser login and local offline storage are independent of production.
4. Verify the feature on test. Find `image` and `revision` in the successful staging run output (or ask the operator to run the helper's `status` action).
5. Open **Actions → Tabsoff production → Run workflow**, choose `tabsoff`, `promote`, and paste those exact two values. Approve the production environment. Only that previously staged digest can be promoted. Production stays on <https://todo.tabsoff.ru>.

Never use Portainer's **Pull latest image** for this stack or manually edit the image behind the helper: that bypasses review and invalidates the staged baseline. Portainer remains useful for status and logs. The helper keeps its saved stack source consistent with `/opt/opentodo/docker-compose.yml`.

## Official updates

**Tabsoff official updates** runs daily or manually and opens one `upstream/vX.Y.Z` PR for the newest stable release. It integrates the release with the downstream branch without rebasing or resetting your custom commits. A clean integration explicitly dispatches CI (GitHub bot-created PRs do not trigger normal PR events). Conflicts remain visible and must be resolved before checks/merge. Review the changelog and CI, merge, verify staging, then promote manually. Never auto-merge upstream updates.

## Restore and failure recovery

Promotion briefly puts production in maintenance mode, stops it, saves its full data directory and exact old Compose/image, then starts the tested image. A failed health check automatically restores the paired old image and data. Rollback invokes OpenTodo's official restore command so its sync generation rotates and devices reseed. It preserves the displaced directory for recovery.

For a later deliberate rollback, run **Tabsoff production** with `rollback`; image/revision inputs are ignored. This returns server data to the **pre-update snapshot**, including undoing subsequent server-side changes. Offline/pending operations can sync again afterward. Inspect important post-update changes before rollback; displaced files remain under the snapshot for recovery. Do not simply run an older image against a migrated database.

Snapshots: `/var/backups/opentodo-releases/<UTC timestamp>/` (root only). Retain the latest three; snapshots containing displaced data require operator cleanup. Existing daily backups remain independent. Disk headroom is checked before changes. No global Docker pruning is performed.

After a killed/interrupted deployment, `/var/lib/opentodo-release/pending.json` blocks further writes. The operator inspects its snapshot and maintenance state. With the server stopped, restore the full snapshot and then invoke the paired old image's official restore command using `restore.tar.gz`; restore `compose.json`, synchronize Portainer's stack source, start and check health, then clear the pending marker and maintenance snippet. Do not clear the marker merely to retry a newer release. The root helper's `restore(Path(snapshot))` function provides this same recovery path from an operator-owned Python session.

## Installation and credentials

The root helper is installed manually as `/usr/local/sbin/opentodo-release` (root-owned, mode 0755). Workflows cannot overwrite it. `/etc/caddy/opentodo-release.caddy` is imported inside the production site block; normally it removes the maintenance header, and returns 503 during maintenance. Test uses loopback port 8081 and a separate Caddy login; production uses 8080.

Create Linux user `opentodo-deploy` with no password and two dedicated SSH keys. Each authorized key uses `restrict,command="sudo -n /usr/local/sbin/opentodo-release --stage-only"` or `--production-only`; sudo permits exactly these two command/argument combinations. Each receives bounded JSON on stdin. The staging key cannot promote or roll back production; the production key cannot select untested images. No shell, forwarding or arbitrary image registry is allowed.

GitHub configuration:

- Default branch `tabsoff`; allow Actions to create PRs.
- Environment secrets named `OPENTODO_DEPLOY_KEY`: separate private keys in `staging` and `production` (never commit them or set a repository-wide fallback).
- Repository variable `OPENTODO_DEPLOY_KNOWN_HOSTS`: operator-verified SSH host key for 89.223.70.53.
- Environments `staging` and `production`; production requires the owner to review and only permits the `tabsoff` branch. Self-review is allowed for a single-person installation.
- Registry credentials use each workflow's short-lived `GITHUB_TOKEN`; the server uses a temporary Docker login and removes it after pulling. Application data and backups never leave the VPS.

Verify helper tests with `python3 -m unittest discover -s scripts/tabsoff -p test_release.py -v`. Verify native restore against a disposable synthetic database using the installed image before enabling production promotion. Keep root recovery access independent of the workflow key. For key rotation, replace the restricted authorized key and GitHub secret together.
