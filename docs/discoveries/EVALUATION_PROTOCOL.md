# LEONES Discovery Evaluation Protocol

## Purpose

Every discovery published by the LEONES radar must contain two human-readable layers:

1. **What it does** — a short functional explanation understandable without reading the source code.
2. **Why it matters** — an assessment of its potential importance for LEONES, including which part of the local agentic stack it could improve and why.

The second layer is not a generic label. It is an explicit intervention by the LEONES evaluation process.

## Required discovery record

Each discovery should contain:

- Project name
- Official URL
- Discovery date
- Category
- Licence and evidence URL
- Open/Copyleft classification
- Functional summary
- Potential importance to LEONES
- Candidate stack component affected
- Evidence available
- Evaluation status
- Recommendation
- Risks or limitations

## Importance assessment

Use a concise assessment such as:

- **High potential** — could materially improve a core LEONES capability, reduce hardware requirements, improve agent reliability/UX, or replace a weak stack component.
- **Medium potential** — useful improvement or complementary capability, but not yet a core candidate.
- **Exploratory** — interesting technology requiring evidence or testing before its relevance can be established.
- **Low potential** — technically relevant but unlikely to change recommended LEONES stacks.

Do not infer importance solely from popularity, stars or marketing claims.

## Bot hand-off

The discovery bot should create a structured candidate record and request an evaluation step. The evaluator must then add the functional explanation and potential-importance assessment before the discovery can move to **Verified** or **Recommended**.

The bot may automate collection and preparation, but it must not fabricate evaluation results.

## Future API/agent interface

The project should support a future bot-to-evaluator call containing:

```json
{
  "project": "...",
  "url": "...",
  "category": "...",
  "license_evidence": "...",
  "discovery_date": "...",
  "candidate_reason": "...",
  "status": "discovered"
}
```

The evaluator response should return:

```json
{
  "functional_summary": "...",
  "potential_importance": "high|medium|exploratory|low",
  "stack_component": "...",
  "evidence": ["..."],
  "limitations": ["..."],
  "recommendation": "...",
  "status": "evaluating|verified|recommended|rejected"
}
```

No personal data is required or permitted in this interface.
