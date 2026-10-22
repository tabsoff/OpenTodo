# Tasks

## 1. Test installation

- [ ] 1.1 Install isolated test Compose/Caddy configuration and record access instructions; verify HTTPS health and disjoint data mounts while production stays healthy.

## 2. Release tooling

- [ ] 2.1 Implement restricted deployment helper, migration rehearsal, paired backup/restore and operator runbook; verify rejection tests and an isolated Docker restore with a rotated sync generation.
- [ ] 2.2 Add CI image tags, staging/manual production workflows and stable-release PR automation; verify repository checks, workflow validation and configured restricted credentials.

## 3. Integration

- [ ] 3.1 Run make check and full upstream CI on the fork, validate OpenSpec, then verify a successful custom build reaches the test instance with production unchanged.
