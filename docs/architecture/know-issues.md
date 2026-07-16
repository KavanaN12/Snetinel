# Known Issues

This document tracks all significant issues encountered during development, their root causes, fixes, and lessons learned.

---

## Issue 001 — bcrypt / passlib Compatibility

**Date**

2026-07-16

### Symptoms

```text
AttributeError:
module 'bcrypt' has no attribute '__about__'
```

Registration endpoint returned HTTP 500.

### Root Cause

`passlib==1.7.4` is incompatible with newer releases of the `bcrypt` package.

### Solution

Pin the dependency versions:

```txt
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
```

Rebuild the Docker image without cache.

```bash
docker compose down
docker compose build --no-cache
docker compose up
```

### Prevention

Pin security-critical dependencies instead of relying on the latest transitive versions.

### Status

✅ Resolved

### Lessons Learned

Always verify dependency compatibility before debugging application logic.