# Enforcing the Agent Policy

Instruction files are guidance, not an access-control boundary. A model may ignore them, and ordinary Git files cannot by themselves guarantee that no unauthorized change reaches the main branch.

For enforceable protection, configure the hosting platform and repository permissions:

1. Protect the default branch and disallow direct unreviewed pushes.
2. Require pull requests and approval from a designated maintainer for changes to the interpreter, parser, type system, grammar, semantic contract, conformance tests, and golden baselines.
3. Require existing CI checks to pass before merge. Use the actual status-check names exposed by the repository; do not invent check names in branch settings.
4. Prevent an author from approving their own changes where the platform supports it.
5. Restrict who can bypass branch protection.
6. Require review when changes modify `AGENTS.md`, agent adapters, the semantic contract, or tests that enforce compatibility.
7. Periodically audit rules and permissions so they match the repository's actual layout and workflow.

Do not add a new CI workflow or install enforcement tooling as part of merely adding this policy pack. First inspect the existing repository CI and ask for approval before changing enforcement configuration. This avoids overwriting current gates or introducing unverified build dependencies.
