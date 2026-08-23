---
name: sql-reviewer
description: Review SQL queries for performance, indexing, and anti-patterns
when_to_use: writing or optimizing database queries
---
# SQL Review Guidelines

When reviewing or writing SQL:
1. Always check for proper index utilization.
2. Avoid `SELECT *`; specify explicit column names.
3. Use parameterized queries to prevent SQL injection.
4. Ensure `WHERE` clauses do not use functions on indexed columns.
