---
applyTo: "**/Tests/**/*.py,**/tests/**/*.py"
---

Follow `AGENTS.md` and `docs/engineering/TESTING_POLICY.md`. Tests must verify specified behavior rather than merely mirror implementation details. Preserve regression tests and golden baselines. Never weaken or delete a failing assertion to obtain a pass. When an intentional semantic change is authorized, explain the old and new behavior and update tests only to reflect the approved specification.
