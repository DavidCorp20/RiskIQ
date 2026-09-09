# RiskIQ Decision Engine

The Decision Engine is the core of RiskIQ.

## Pipeline

```text
Portfolio Facts
      ↓
Condition Evaluation
      ↓
Rule Match
      ↓
Decision Generation
      ↓
Action Plan
      ↓
Execution / Approval
      ↓
Audit Event
```

## Design requirements

1. Deterministic evaluation.
2. Typed operands and operators.
3. Versioned rules.
4. Explainable evaluation results.
5. Safe action registry.
6. No arbitrary user code execution.
7. Simulation support before activation.
8. Tenant-aware execution.

## Rule modes

- `recommendation`: produce a recommendation only.
- `approval_required`: generate a decision pending approval.
- `automatic`: execute only actions explicitly allowed by the action registry.

## Future DSL

A controlled risk DSL may eventually support expressions such as:

```text
risk_score = par30 * 0.35 + par90 * 0.40 + roll_30_60 * 0.25
```

The DSL must compile into the same normalized rule representation used by the visual builder and formula editor.
