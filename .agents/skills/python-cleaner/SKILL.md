---
name: python-cleaner
description: Formats and checks PEP 8 conventions
when_to_use: reviewing Python code, refactoring scripts, enforcing style standards, pre-commit linting, CI/CD quality gates
---

# Python Cleaner Guidelines

When reviewing or formatting Python code:

1. **Enforce PEP 8**: 4-space indent, max 79-char lines, blank lines between top-level definitions.
2. **Group imports**: stdlib → third-party → local, separated by blank lines.
3. **Naming conventions**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants.
4. **Remove dead code**: Unused imports, variables, and unreachable statements.
5. **Prefer f-strings**: Over `.format()` or `%` formatting.
6. **Use context managers**: `with` statements for files, sockets, DB connections.
7. **Avoid bare `except:`**: Catch specific exception types.
8. **Add docstrings**: All public functions, classes, and modules.
9. **Limit line complexity**: Break long expressions; avoid deeply nested logic.
10. **Run formatters/linters**: `black`, `ruff`, or `flake8` in CI.