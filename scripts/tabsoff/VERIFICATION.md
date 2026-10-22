# Verification — 2026-10-22

- PR #3 full CI: https://github.com/tabsoff/OpenTodo/actions/runs/39843763506 — successful on source `b685bccca290df762a170fd7672ec4bdfd92f6cc`.
- Merge `7704b5ad1e8162a231b0ee6a4aa9f7a6e63f0ec4` has the same Git tree as that tested source.
- 18 Python tests and 46 repository checks passed. The original application test/build/security/browser gates and every part of `make check` passed through the official split CI jobs.
- The deployment lifecycle passed on the exact built/scanned CI application image. Disposable real containers verified task survival, paired image/data rollback, rotated sync generation and recovery from a real failed candidate container.
- The root helper installer was run twice successfully with identical SHA256 `61778fb1a3d8d2172a0991fab22bc2acd462bac7dc497f00428802a75f80352f`; the previous root-owned executable is retained. The live restricted status call matches this checksum and candidate preparation passes without changing production.
- Production remains the official v0.9.0 image. No application source, schema, production container or production data was changed by the tooling installation.

## Post-merge checks

- Shared manual staging: https://github.com/tabsoff/OpenTodo/actions/runs/39847269227 — successful. It reuses the existing fully checked published image, validates its source CI/publication, checks the installed helper checksum, privately rehearses migrations and deploys isolated staging. Production was not promoted.
- Operator-only push CI: https://github.com/tabsoff/OpenTodo/actions/runs/39847294475 — successful. Only repository/Python checks and the disposable deployment lifecycle ran; application/server/browser/platform/image jobs were skipped, including image publication.
- The duplicate full post-merge run https://github.com/tabsoff/OpenTodo/actions/runs/39847175030 was canceled before publication after its Playwright installation stalled. Its Git tree is identical to the fully successful PR run above; no application source changed. This was a deliberate operator cancellation of redundant verification, not a change removing future push/release gates or a `[skip ci]` commit.
- Production preparation consumed the live restricted `status` response in read-only mode and selected the recorded tested candidate. The production environment's owner-review and branch restrictions were confirmed through GitHub's read-only API. An attempted production-workflow test dispatch was rejected by automatic approval review because it requested `promote` without separate authorization for a real production release; it was not retried. No production workflow was started or approved. The full mutation/rollback path was tested only on disposable synthetic instances.
