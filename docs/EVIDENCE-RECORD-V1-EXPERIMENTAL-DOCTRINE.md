# Evidence Record v1 — Experimental Doctrine

Status: FROZEN IMPLEMENTATION BASELINE
Milestone: Evidence Record v1 -> End-to-End Experimental Validation
Date: 2026-10-04

Kronos is the execution plane. MANIFEX is the integrity, provenance, evidence, and qualification boundary. Human authority remains separate from execution and evidence.

## Frozen rule

Evidence is a record of reality, not a mechanism for manufacturing success.

No architectural expansion or feature additions to Evidence Record v1 should occur unless the end-to-end experiment exposes an actual defect or unmet requirement.

## Frozen state

- Kronos execution contract: IMPLEMENTED
- Kronos evidence generation: IMPLEMENTED
- MANIFEX evidence receiver: IMPLEMENTED
- First-class evidence storage: IMPLEMENTED
- Hash recomputation: IMPLEMENTED
- Duplicate protection: IMPLEMENTED
- Append-only evidence ledger: IMPLEMENTED
- BuildIndex integration: IMPLEMENTED
- Qualification separation: PRESERVED
- Exact source checkout: BLOCKED
- Commit-bound execution: NOT ESTABLISHED
- End-to-end execution: PENDING
- Independent verification: NOT STARTED
- Qualification: NOT QUALIFIED

## Experimental chain

EXACT CHECKOUT
-> KRONOS LOCAL EXECUTION
-> ExecutionResult
-> KRONOS EVIDENCE v1
-> MANIFEX INTEGRITY VERIFICATION
-> FIRST-CLASS EVIDENCE RECORD
-> EVIDENCE LEDGER + BuildIndex
-> QUALIFICATION GATE

## Acceptance dimensions

1. Integrity: MANIFEX rejects request, result, and evidence mutations.
2. Provenance: execution is bound to the exact source revision and recorded environment.
3. Non-escalation: registration preserves NOT_QUALIFIED/NOT_MEASURED and rejects QUALIFIED or authority injection.
4. Authority separation: execution evidence remains separate from authorization.

## Symmetric result doctrine

- PASS -> recorded as PASS
- FAIL -> recorded as FAIL
- BLOCKED -> recorded as BLOCKED
- TAMPERED -> rejected and recorded as an integrity failure
- ESCALATED -> rejected
- UNKNOWN -> remains UNKNOWN / NOT_MEASURED

A provider outage is not silently converted into a test result. Missing evidence is not inferred.

## Required experiment package

The eventual package must capture at minimum:

experiment_id, Kronos repository, Kronos commit SHA, MANIFEX repository, MANIFEX commit SHA, execution_id, request_id, mission_id, provider, command, phase, environment, start time, finish time, exit code, stdout, stderr, stdout hash, stderr hash, request hash, result hash, evidence hash, MANIFEX registration result, BuildIndex asset ID, ledger event, qualification decision.

A top-level experiment manifest hash should bind the complete package.

## Falsification rule

The evidence system must be capable of proving the architecture wrong.

If execution reveals a hash mismatch, broken commit binding, mutable evidence, qualification bypass, authority escalation, or incorrect provider reporting, preserve the failure and investigate it. Do not modify the evidence layer merely to produce a successful outcome.

## Current blocker

Exact checkout/execution is currently blocked by the execution environment's inability to resolve GitHub. This is an environmental execution blocker, not a test result.

## Next legitimate state transition

FROZEN IMPLEMENTATION
-> EXACT CHECKOUT AVAILABLE
-> CONTROLLED EXECUTION
-> EVIDENCE GENERATION
-> INTEGRITY VERIFICATION
-> MANIFEX REGISTRATION
-> IMMUTABLE EVIDENCE RECORD
-> QUALIFICATION DECISION

The next meaningful change to the implementation should come from the experiment itself, not from continued architectural redesign.
