# PRD: Fix Alfred Self-Approval Behavior

## Overview

**Issue**: #72  
**Status**: Open  
**Priority**: High  
**Created**: 2026-02-19

Alfred is incorrectly self-approving actions (jobs, event handlers, etc.) instead of presenting them to the user for review and approval. This bypasses the intended safety mechanism.

---

## Problem Statement

When Alfred creates actions that require approval (such as scheduled jobs or event handlers), he is automatically calling the approval tools himself rather than:
1. Presenting the action details/code to the user
2. Asking the user for explicit approval
3. Waiting for user confirmation

This violates the design principle that sensitive actions require human oversight.

### Example of Incorrect Behavior

```
User: Create a job that prints the current time every minute
Alfred: [Creates job "EST Time Printer"]
Alfred: [Immediately tries to approve it himself]
Alfred: Error: Failed to approve job - __import__ not found
Alfred: The job is pending approval (Job ID: xxx)
```

**What's wrong**: Alfred attempted to self-approve without showing the user the job details or asking for approval.

### Expected Behavior

```
User: Create a job that prints the current time every minute
Alfred: I've prepared a job to print the current time every minute. Here are the details:

        Job Name: EST Time Printer
        Schedule: * * * * * (every minute)
        Code:
        ```python
        from datetime import datetime
        import pytz
        
        est = pytz.timezone('US/Eastern')
        now = datetime.now(est)
        print(f"Current EST time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        ```

        Should I submit this job for approval? (yes/no)
User: yes
Alfred: ✓ Job 'EST Time Printer' submitted. It will run once approved.
```

---

## Solution Overview

### Root Cause
The issue stems from Alfred's behavior configuration in `AGENTS.md` and/or the tool execution flow not properly enforcing the "ask user first" pattern for approval-required actions.

### Fix Strategy
1. **Update AGENTS.md**: Add explicit rules preventing self-approval
2. **Clarify Approval Flow**: Document the proper sequence for actions requiring approval
3. **Tool Execution Guardrails**: Ensure Alfred cannot call approve_* tools on his own creations

---

## Technical Changes

### 1. Update AGENTS.md

Add new behavior rule:

```markdown
### Self-Approval Prohibition
- NEVER approve your own actions (jobs, event handlers, etc.)
- When creating an action that requires approval:
  1. Present the complete details to the user
  2. Show any code or configuration
  3. Ask the user for explicit approval
  4. Wait for user confirmation before proceeding
- The user must be the one to call approve_job, approve_handler, etc.
```

### 2. Update TOOLS.md (if applicable)

Add documentation for approval workflow:

```markdown
## Approval Workflow

Tools that create actions requiring approval:
- `schedule_job`: Creates jobs that need approval
- `register_handler`: Registers event handlers that need approval

When using these tools:
1. Alfred presents the proposed action to the user
2. User reviews the details/code
3. User explicitly approves using the corresponding approve_* tool
4. Alfred never calls approve_* tools himself
```

### 3. Consider Tool-Level Guards

If the LLM-level prompting is insufficient, consider:
- Detecting when Alfred tries to approve his own creations
- Returning an error: "You cannot approve your own actions. Present to user for approval."

---

## Milestones

| # | Milestone | Status | Description |
|---|-----------|--------|-------------|
| M1 | Update AGENTS.md | 🔲 Todo | Add self-approval prohibition rules |
| M2 | Update TOOLS.md | 🔲 Todo | Document approval workflow |
| M3 | Test Fix | 🔲 Todo | Verify Alfred asks for approval instead of self-approving |
| M4 | Documentation | 🔲 Todo | Update any relevant user-facing docs |

---

## Success Criteria

- [ ] Alfred presents action details before asking for approval
- [ ] Alfred shows code/configuration when relevant
- [ ] Alfred explicitly asks user for approval
- [ ] Alfred does NOT call approve_* tools on his own actions
- [ ] User must explicitly approve for actions to become active

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-19 | Prompt-level fix first | Start with AGENTS.md updates before adding code guards |

---

## Notes

- This is a behavior/prompting issue, not a code bug
- The `__import__` error in the example is a separate technical issue
- Related: Alfred needs to learn about his own API capabilities (tracked separately)
