# Codex Workflow Playbook

**Purpose:** Provides repeatable instructions for feature, bugfix, refactor, and evaluation tasks.

## Feature workflow

1. Read AGENTS.md and relevant tuning doc.
2. Create a short implementation plan.
3. Implement the smallest viable vertical slice.
4. Add tests.
5. Run tests.
6. Update docs.
7. Summarize validation and risks.

## Bugfix workflow

1. Reproduce with a test.
2. Fix root cause, not symptom.
3. Add regression coverage.
4. Verify no safety or cost regression.

## Refactor workflow

1. Preserve behavior with tests before changing structure.
2. Move code in small steps.
3. Run tests after each step.
4. Update imports and docs.

## Evaluation workflow

1. Add scenario to `evals/restaurant_test_cases.json` or `evals/red_team_prompts.json`.
2. Define expected behavior.
3. Run eval script or tests.
4. Compare with baseline.
5. Record decision in release notes.
