# Monitoring and KQL

## Azure OpenAI throttle alert

```kusto
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.COGNITIVESERVICES"
| where StatusCode == 429 or statusCode_d == 429
| summarize Throttled=count() by bin(TimeGenerated, 5m)
| where Throttled > 10
```

## Content safety block rate

```kusto
customEvents
| where name == "content_safety_decision"
| summarize total=count(), blocked=countif(tostring(customDimensions.decision) == "block") by bin(timestamp, 15m)
| extend blockRate = todouble(blocked) / todouble(total)
```

## Token usage by feature

```kusto
customMetrics
| where name in ("prompt_tokens", "completion_tokens")
| summarize tokens=sum(value) by name, tostring(customDimensions.feature), bin(timestamp, 1h)
```

## Document Intelligence failures

```kusto
AzureDiagnostics
| where ResourceType has "COGNITIVESERVICES"
| where OperationName has "Analyze"
| summarize errors=countif(statusCode_d >= 500), total=count() by bin(TimeGenerated, 5m)
| extend errorRate = todouble(errors) / todouble(total)
| where errorRate > 0.05
```
