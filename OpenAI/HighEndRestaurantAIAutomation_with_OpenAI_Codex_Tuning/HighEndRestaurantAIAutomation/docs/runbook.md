# Operations Runbook

## Incident: Azure OpenAI 429 throttling
1. Check quota and deployment TPM/RPM.
2. Confirm SDK retry with exponential backoff.
3. Reduce max tokens or batch non-urgent tasks.
4. Temporarily route low-priority features to cached answers.
5. Request quota increase or add deployment capacity.

## Incident: harmful output detected
1. Block response and show safe escalation message.
2. Record prompt, retrieved document IDs, content safety scores, and model deployment name.
3. Add or update blocklist if needed.
4. Add test case to `evals/red_team_prompts.json`.
5. Deploy updated safety policy through CI/CD.

## Incident: invoice extraction incorrect
1. Verify document type and image quality.
2. Use Document Intelligence confidence scores.
3. Route to human review if below threshold.
4. Add sample to custom training dataset if pattern recurs.

## Rollback
- Revert app slot.
- Repoint AI Search alias to previous index.
- Use previous Azure OpenAI deployment name.
- Disable feature flag.
