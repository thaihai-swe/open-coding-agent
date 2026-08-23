---
domain: example
triggers: [example, sample, demo, template, walkthrough]
---

# Domain — Glossary

This file is an optional domain-pack example. Replace it with adopter domain
terms; keep project-wide and workflow vocabulary in
`corebase-specharness/project/glossary.md`.

> Ownership: Collaborative — skill-updated + user-maintained.
> Updated by: `/context-memory` post-ship sync when new terms emerge from a completed feature.
> Read by: `/spec-requirements`, `/spec-plan`, `/spec-implement` to enforce consistent naming.

This is a worked example of a domain pack glossary. Replace with your domain's
ubiquitous language. Nested packs live at
`corebase-specharness/memories/domain/<name>/glossary.md`. This flat file is the shipped
default pack and is selected when its `triggers` match the request intent.

## Ubiquitous Language

| Term | Definition | Example Usage |
|-|-|-|
| Widget | A reusable UI component with a defined contract | "Every widget exposes an `onMount` callback." |
| Gadget | A backend service that widgets call | "The gadget returns a paginated response." |
| Session | An authenticated user interaction with a bounded TTL | "Sessions expire after 30 minutes of inactivity." |

## Notes

- Replace this example pack with your actual domain vocabulary.
- Keep terms precise — ambiguous terms cause agents to make inconsistent naming choices.
- Update this file during `/context-memory` Post-Ship Sync when new terms emerge.
