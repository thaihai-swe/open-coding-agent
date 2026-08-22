---
schema_version: 1
---

# Feature Status: 1-the-agent-loop

- Phase: Done
- Delivery profile: Complex
- Status: Active
- Active task: None
- Next step: /context-memory

## Intake
- Input type: `new_spec` (roadmap Session 01 over existing brownfield loop)
- One-line restatement: Formalize the provider-neutral complete contract and a bounded REPL tool loop.
- Why now: User invoked `/spec-requirements` for Provider Foundation & Minimal Agent Loop.
- Primary user/outcome: Operator sends a prompt; model text and tool results land in persisted history; loop stops on no tools or max_turns.
- Changed boundaries / public seams: Provider complete contract; `QueryEngine.turn` termination reason; `max_turns` (default 8).
- Preserved behavior: config cascade, exit 2/0/130, authorize/deny, session redaction, CLI flags.
- Risk flags: protocol + turn-limit change on existing engine
- Known constraints: stdlib only; slug on disk is `1-the-agent-loop`
- Blocking unknowns: none
- Familiarity / urgency: assumed Familiar / Normal

## Progress
- [x] Research/spec complete
- [x] Spec approved
- [x] Plan/tasks complete (Moderate/Complex only)
- [x] Plan approved
- [x] Implementation complete
- [x] Validation complete

## Blockers / Decisions
- Blocker: none
- Locked decision: Formalize Provider protocol + max_turns; profile Complex; continue-on-tool_calls not stop_reason alone

## Blocked Recovery
- Reason:
- Owner:
- Evidence:
- Next review at:
- Recommended handoff:
