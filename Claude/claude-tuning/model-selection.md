# model-selection.md — Choosing the Right Claude Model

> **Purpose**: Decision framework and cost calculator for selecting Claude Opus 4, Sonnet 4, or Haiku 4.5 for every task. Covers model profiles, cascade patterns, cost comparison, evaluation-driven selection, and version pinning.
> **Who This Is For**: Junior developers picking a model for the first time; senior engineers optimizing cost-quality tradeoffs at scale.
> **Owner**: jose@hybridgenai.com

---

## Navigation

1. [Current Model Lineup (2026)](#1-current-model-lineup-2026)
2. [Decision Framework — Which Model When](#2-decision-framework--which-model-when)
3. [Task-Based Model Mapping](#3-task-based-model-mapping)
4. [Cost-Quality Trade-off Calculator](#4-cost-quality-trade-off-calculator)
5. [Multi-Model Cascade Pattern](#5-multi-model-cascade-pattern)
6. [Model Selection by Use Case](#6-model-selection-by-use-case)
7. [Evaluation-Driven Model Selection](#7-evaluation-driven-model-selection)
8. [Version Pinning and Migration Strategy](#8-version-pinning-and-migration-strategy)
9. [Environment-Based Configuration](#9-environment-based-configuration)
10. [Junior Walkthrough — Choose a Model for Your First App](#10-junior-walkthrough--choose-a-model-for-your-first-app)
11. [Senior Patterns — Model Strategy at Scale](#11-senior-patterns--model-strategy-at-scale)
12. [Tips, Tricks, and Gotchas](#12-tips-tricks-and-gotchas)
13. [Quick Reference Cheatsheet](#13-quick-reference-cheatsheet)

---

## 1. Current Model Lineup (2026)

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                        CLAUDE MODEL COMPARISON (2026)                              │
├──────────────────┬────────────────────────────┬───────────────────────────────────┤
│ Model            │ API String                 │ Context Window                    │
├──────────────────┼────────────────────────────┼───────────────────────────────────┤
│ Claude Opus 4    │ claude-opus-4-6             │ 200,000 tokens                    │
│ Claude Sonnet 4  │ claude-sonnet-4-6           │ 200,000 tokens                    │
│ Claude Haiku 4.5 │ claude-haiku-4-5-20251001   │ 200,000 tokens                    │
└──────────────────┴────────────────────────────┴───────────────────────────────────┘

┌──────────────────┬──────────────────────┬───────────────────────────────────────┐
│ Model            │ Pricing ($/MTok)     │ Strengths                             │
│                  │ Input / Output       │                                       │
├──────────────────┼──────────────────────┼───────────────────────────────────────┤
│ Claude Opus 4    │ $15.00 / $75.00      │ Frontier reasoning, complex code,     │
│                  │                      │ strategic analysis, highest accuracy  │
├──────────────────┼──────────────────────┼───────────────────────────────────────┤
│ Claude Sonnet 4  │  $3.00 / $15.00      │ Strong reasoning + speed balance,     │
│                  │                      │ best value for production workloads   │
├──────────────────┼──────────────────────┼───────────────────────────────────────┤
│ Claude Haiku 4.5 │  $0.80 /  $4.00      │ Fastest, cheapest, reliable for       │
│                  │                      │ simple tasks at high volume           │
└──────────────────┴──────────────────────┴───────────────────────────────────────┘

Cost ratios (relative to Haiku):
  Haiku:  1× baseline
  Sonnet: ~4× more expensive on input, ~4× on output
  Opus:   ~19× more expensive on input, ~19× on output

Rule: Every task moved from Opus → Sonnet saves ~19×. Every Sonnet → Haiku saves ~4×.
```

---

## 2. Decision Framework — Which Model When

```
                        START HERE
                           │
                           ▼
            ┌──────────────────────────┐
            │ Is it a routing/          │
            │ classification/           │     YES → 🟢 HAIKU
            │ simple extraction task?   │──────────────────────
            └──────────────────────────┘
                           │ NO
                           ▼
            ┌──────────────────────────┐
            │ Is the user waiting and  │
            │ it's latency-critical    │     YES → 🟢 HAIKU (or Sonnet w/ caching)
            │ (< 800ms TTFT needed)?   │──────────────────────
            └──────────────────────────┘
                           │ NO
                           ▼
            ┌──────────────────────────┐
            │ Standard task: Q&A,      │
            │ RAG, summarization,      │     YES → 🟡 SONNET (default choice)
            │ code gen, extraction?    │──────────────────────
            └──────────────────────────┘
                           │ NO
                           ▼
            ┌──────────────────────────┐
            │ Does this require:       │
            │ - Extended autonomous    │
            │   multi-step reasoning?  │
            │ - Complex debugging      │     YES → 🔴 OPUS
            │   across many files?     │──────────────────────
            │ - Deep strategic         │
            │   analysis with          │
            │   trade-offs?            │
            │ - Measured Sonnet fail?  │
            └──────────────────────────┘
```

### Sonnet vs Opus Decision

```python
# The most common mistake: using Opus when Sonnet is sufficient
# Only use Opus if you have MEASURED that Sonnet fails to meet quality threshold

# ❌ Wrong: "This is important so we'll use Opus"
model = "claude-opus-4-6"  # Without measuring quality gap

# ✅ Right: Run eval, compare, promote only if needed
def choose_model_for_task(task_type: str, measured_sonnet_score: float) -> str:
    """
    Use the cheapest model that meets your quality threshold.
    
    Args:
        task_type:              Type of task being performed
        measured_sonnet_score:  Sonnet's quality score on your eval dataset
    
    Returns:
        Model API string
    """
    QUALITY_THRESHOLD = 0.85  # Require 85% quality score
    
    # If Sonnet meets the threshold, use it
    if measured_sonnet_score >= QUALITY_THRESHOLD:
        return "claude-sonnet-4-6"
    
    # Only escalate to Opus if Sonnet measurably falls short
    return "claude-opus-4-6"
```

---

## 3. Task-Based Model Mapping

```python
import os

# ── Default model configuration ───────────────────────────────────────────
# Override any task model via environment variables for easy A/B testing
# and gradual rollout without code changes.
#
# Set in Azure App Service / GitHub Actions / .env file:
#   CLAUDE_MODEL_ROUTING=claude-haiku-4-5-20251001
#   CLAUDE_MODEL_GENERATION=claude-sonnet-4-6
#   CLAUDE_MODEL_ANALYSIS=claude-opus-4-6

TASK_MODEL_CONFIG = {
    # ── Classification & Routing (Haiku) ──────────────────────────────
    "classify_intent": os.getenv("CLAUDE_MODEL_ROUTING", "claude-haiku-4-5-20251001"),
    "detect_language": os.getenv("CLAUDE_MODEL_ROUTING", "claude-haiku-4-5-20251001"),
    "route_query":     os.getenv("CLAUDE_MODEL_ROUTING", "claude-haiku-4-5-20251001"),
    "binary_check":    os.getenv("CLAUDE_MODEL_ROUTING", "claude-haiku-4-5-20251001"),
    "extract_field":   os.getenv("CLAUDE_MODEL_ROUTING", "claude-haiku-4-5-20251001"),
    "sentiment_check": os.getenv("CLAUDE_MODEL_ROUTING", "claude-haiku-4-5-20251001"),
    
    # ── Standard Generation (Sonnet) ──────────────────────────────────
    "rag_answer":           os.getenv("CLAUDE_MODEL_GENERATION", "claude-sonnet-4-6"),
    "summarise_document":   os.getenv("CLAUDE_MODEL_GENERATION", "claude-sonnet-4-6"),
    "generate_description": os.getenv("CLAUDE_MODEL_GENERATION", "claude-sonnet-4-6"),
    "code_generation":      os.getenv("CLAUDE_MODEL_GENERATION", "claude-sonnet-4-6"),
    "translate_text":       os.getenv("CLAUDE_MODEL_GENERATION", "claude-sonnet-4-6"),
    "extract_invoice":      os.getenv("CLAUDE_MODEL_GENERATION", "claude-sonnet-4-6"),
    "wine_recommendation":  os.getenv("CLAUDE_MODEL_GENERATION", "claude-sonnet-4-6"),
    "tasting_menu_copy":    os.getenv("CLAUDE_MODEL_GENERATION", "claude-sonnet-4-6"),
    "email_draft":          os.getenv("CLAUDE_MODEL_GENERATION", "claude-sonnet-4-6"),
    
    # ── Complex Analysis (Opus) ────────────────────────────────────────
    "strategic_analysis":   os.getenv("CLAUDE_MODEL_ANALYSIS", "claude-opus-4-6"),
    "complex_agent":        os.getenv("CLAUDE_MODEL_ANALYSIS", "claude-opus-4-6"),
    "annual_report":        os.getenv("CLAUDE_MODEL_ANALYSIS", "claude-opus-4-6"),
    "debug_complex_code":   os.getenv("CLAUDE_MODEL_ANALYSIS", "claude-opus-4-6"),
    "multi_step_research":  os.getenv("CLAUDE_MODEL_ANALYSIS", "claude-opus-4-6"),
}

def get_model_for_task(task: str) -> str:
    """
    Get the configured model for a given task.
    
    Args:
        task: Task identifier (must match a key in TASK_MODEL_CONFIG)
    
    Returns:
        Model API string
    
    Raises:
        ValueError if task is not in the configuration
    
    Usage:
        model = get_model_for_task("wine_recommendation")
        # → "claude-sonnet-4-6"
        
        model = get_model_for_task("classify_intent")
        # → "claude-haiku-4-5-20251001"
    """
    if task not in TASK_MODEL_CONFIG:
        raise ValueError(
            f"Unknown task: '{task}'. Available tasks: {list(TASK_MODEL_CONFIG.keys())}"
        )
    return TASK_MODEL_CONFIG[task]
```

---

## 4. Cost-Quality Trade-off Calculator

```python
from dataclasses import dataclass

@dataclass
class ModelPricing:
    input_per_million: float   # $ per million input tokens
    output_per_million: float  # $ per million output tokens

# Approximate 2026 pricing (check docs.anthropic.com for current rates)
PRICING = {
    "claude-opus-4-6":          ModelPricing(input_per_million=15.00,  output_per_million=75.00),
    "claude-sonnet-4-6":        ModelPricing(input_per_million=3.00,   output_per_million=15.00),
    "claude-haiku-4-5-20251001": ModelPricing(input_per_million=0.80,   output_per_million=4.00),
}

def estimate_monthly_cost(
    daily_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    model: str,
    working_days_per_month: int = 30,
) -> dict:
    """
    Estimate monthly Claude API cost for a given workload.
    
    Args:
        daily_requests:          Average requests per day
        avg_input_tokens:        Average input tokens per request
        avg_output_tokens:       Average output tokens per request
        model:                   Model API string
        working_days_per_month:  Days of operation per month
    
    Returns:
        dict with daily_cost_usd, monthly_cost_usd, cost_per_request_usd
    
    Example:
        # Classify 5,000 requests/day with Haiku
        cost = estimate_monthly_cost(5000, 500, 20, "claude-haiku-4-5-20251001")
        # → {"monthly_cost_usd": 7.20, ...}
        
        # Same volume with Sonnet
        cost = estimate_monthly_cost(5000, 500, 20, "claude-sonnet-4-6")
        # → {"monthly_cost_usd": 27.00, ...}  ← 3.75× more expensive
    """
    p = PRICING[model]
    
    input_cost_per_request  = (avg_input_tokens  / 1_000_000) * p.input_per_million
    output_cost_per_request = (avg_output_tokens / 1_000_000) * p.output_per_million
    cost_per_request = input_cost_per_request + output_cost_per_request
    
    daily_cost   = daily_requests * cost_per_request
    monthly_cost = daily_cost * working_days_per_month
    
    return {
        "model":               model,
        "daily_requests":      daily_requests,
        "avg_input_tokens":    avg_input_tokens,
        "avg_output_tokens":   avg_output_tokens,
        "cost_per_request_usd": round(cost_per_request, 6),
        "daily_cost_usd":      round(daily_cost, 2),
        "monthly_cost_usd":    round(monthly_cost, 2),
    }

def compare_models_for_workload(
    daily_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    print_table: bool = True,
) -> dict:
    """
    Compare all three models for the same workload.
    
    Usage:
        compare_models_for_workload(
            daily_requests=10_000,
            avg_input_tokens=2_000,
            avg_output_tokens=500,
        )
    
    Output:
        ┌──────────────────────────────────────────────┐
        │ Workload: 10,000 req/day, 2,000 in + 500 out │
        ├──────────────────────────────┬───────────────┤
        │ Model                        │ Monthly Cost  │
        ├──────────────────────────────┼───────────────┤
        │ claude-haiku-4-5-20251001    │    $276.00    │
        │ claude-sonnet-4-6            │  $2,700.00    │
        │ claude-opus-4-6              │ $13,500.00    │
        └──────────────────────────────┴───────────────┘
    """
    results = {}
    
    for model in PRICING:
        results[model] = estimate_monthly_cost(
            daily_requests, avg_input_tokens, avg_output_tokens, model
        )
    
    if print_table:
        print(f"\nWorkload: {daily_requests:,} req/day, {avg_input_tokens:,} input + {avg_output_tokens:,} output tokens")
        print(f"{'Model':<35} {'Cost/Request':>12} {'Monthly':>12}")
        print("─" * 62)
        for model, cost in results.items():
            short_name = model.split("-")[-2] + "-" + model.split("-")[-1]
            print(f"{model:<35} ${cost['cost_per_request_usd']:>10.4f} ${cost['monthly_cost_usd']:>10,.2f}")
        
        # Show savings vs Opus
        opus_cost = results["claude-opus-4-6"]["monthly_cost_usd"]
        sonnet_cost = results["claude-sonnet-4-6"]["monthly_cost_usd"]
        haiku_cost  = results["claude-haiku-4-5-20251001"]["monthly_cost_usd"]
        print(f"\nSonnet vs Opus: saves ${opus_cost - sonnet_cost:,.2f}/month ({(1 - sonnet_cost/opus_cost)*100:.0f}% reduction)")
        print(f"Haiku vs Opus:  saves ${opus_cost - haiku_cost:,.2f}/month ({(1 - haiku_cost/opus_cost)*100:.0f}% reduction)")
    
    return results

# Real workload example for Lumière restaurant:
# 1,000 chat requests/day with avg 1,500 input + 300 output tokens
compare_models_for_workload(1_000, 1_500, 300)
# Haiku:  ~$42/month  ← If quality is sufficient
# Sonnet: ~$162/month ← Recommended for wine recommendations
# Opus:   ~$810/month ← Only for deep strategy tasks
```

---

## 5. Multi-Model Cascade Pattern

Use cheap models for easy cases; escalate to powerful models only when needed.

```python
from dataclasses import dataclass
import anthropic
import json

@dataclass 
class CascadeResult:
    response: str
    model_used: str
    confidence: float
    escalated: bool

class ModelCascade:
    """
    Cascade through models: Haiku → Sonnet → Opus.
    Start cheap; escalate only when confidence is low.
    
    Cost example for intent classification:
        Without cascade: 100% Sonnet = $0.018 per 1K requests
        With cascade:    80% Haiku + 18% Sonnet + 2% Opus
                        = $0.000375×800 + $0.018×180 + $0.090×20
                        = $0.30 + $3.24 + $1.80 = $5.34 per 1K requests
                        vs $18.00 all-Sonnet = 70% savings
    """
    
    HAIKU  = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-6"
    OPUS   = "claude-opus-4-6"
    
    def __init__(self):
        self.client = anthropic.Anthropic()
    
    def classify(
        self,
        text: str,
        categories: list[str],
        haiku_threshold: float = 0.90,
        sonnet_threshold: float = 0.85,
    ) -> CascadeResult:
        """
        Classify text using cascade.
        
        Args:
            text:              Text to classify
            categories:        Possible classification categories
            haiku_threshold:   Confidence threshold to accept Haiku result (default: 0.90)
            sonnet_threshold:  Confidence threshold to accept Sonnet result (default: 0.85)
        
        Returns:
            CascadeResult with response, model_used, confidence, escalated
        
        Example:
            result = cascade.classify(
                "Do you have a good Pinot Noir?",
                categories=["wine", "menu", "booking", "complaint", "other"],
            )
            print(result.model_used)  # "claude-haiku-4-5-20251001" (high confidence)
            print(result.response)    # "wine"
        """
        cat_str = ", ".join(categories)
        prompt = (
            f"Classify the following text into exactly ONE of these categories: {cat_str}\n"
            f"Return JSON only: {{\"category\": \"<one of the categories>\", \"confidence\": 0.0-1.0}}\n"
            f"Text: {text}"
        )
        
        # Stage 1: Haiku (fastest, cheapest)
        haiku_result = self._call_and_parse(prompt, self.HAIKU, max_tokens=50)
        if haiku_result["confidence"] >= haiku_threshold:
            return CascadeResult(
                response=haiku_result["category"],
                model_used=self.HAIKU,
                confidence=haiku_result["confidence"],
                escalated=False,
            )
        
        # Stage 2: Sonnet (better reasoning)
        sonnet_result = self._call_and_parse(prompt, self.SONNET, max_tokens=50)
        if sonnet_result["confidence"] >= sonnet_threshold:
            return CascadeResult(
                response=sonnet_result["category"],
                model_used=self.SONNET,
                confidence=sonnet_result["confidence"],
                escalated=True,
            )
        
        # Stage 3: Opus (best accuracy for edge cases)
        opus_result = self._call_and_parse(prompt, self.OPUS, max_tokens=50)
        return CascadeResult(
            response=opus_result["category"],
            model_used=self.OPUS,
            confidence=opus_result["confidence"],
            escalated=True,
        )
    
    def analyse(
        self,
        document: str,
        question: str,
        complexity: str = "auto",
    ) -> CascadeResult:
        """
        Analyse a document with appropriate model.
        
        Args:
            document:   Document text
            question:   Analysis question
            complexity: "simple" / "standard" / "complex" / "auto"
        
        If complexity="auto", Haiku estimates complexity before choosing model.
        """
        if complexity == "auto":
            complexity = self._estimate_complexity(document, question)
        
        model_map = {
            "simple":   self.HAIKU,
            "standard": self.SONNET,
            "complex":  self.OPUS,
        }
        model = model_map.get(complexity, self.SONNET)
        
        response = self.client.messages.create(
            model=model,
            max_tokens=1500,
            messages=[{"role": "user", "content": f"{question}\n\n{document}"}]
        )
        
        return CascadeResult(
            response=response.content[0].text,
            model_used=model,
            confidence=1.0,
            escalated=complexity != "simple",
        )
    
    def _call_and_parse(self, prompt: str, model: str, max_tokens: int) -> dict:
        """Call Claude and parse JSON response."""
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        try:
            return json.loads(response.content[0].text)
        except json.JSONDecodeError:
            return {"category": "other", "confidence": 0.0}
    
    def _estimate_complexity(self, document: str, question: str) -> str:
        """Use Haiku to estimate task complexity before choosing model."""
        prompt = (
            f"Rate the complexity of this analysis task as: simple, standard, or complex.\n"
            f"Return one word only.\n\n"
            f"Task: {question}\nDocument length: {len(document)} chars"
        )
        response = self.client.messages.create(
            model=self.HAIKU,
            max_tokens=5,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip().lower()
```

---

## 6. Model Selection by Use Case

### Restaurant AI Task Matrix

| Task | Model | Why | Max Tokens |
|------|-------|-----|------------|
| Route query: wine/menu/booking/other | Haiku | 4-way classification — Haiku handles easily at 99%+ accuracy | 10 |
| Detect guest language | Haiku | Simple detection — Haiku is sufficient | 5 |
| Answer FAQ from static knowledge | Haiku | Low complexity, high volume | 150 |
| Detect allergen keywords in query | Haiku | Pattern detection | 5 |
| Check if query is in scope | Haiku | Binary classification | 5 |
| Wine pairing recommendation | Sonnet | Nuanced flavour reasoning | 400 |
| Summarise supplier invoice | Sonnet | Standard extraction + structured output | 300 |
| Generate tasting menu description | Sonnet | Creative writing with quality bar | 300 |
| Analyse price anomalies in invoices | Sonnet | Pattern analysis across data | 500 |
| Multi-turn guest conversation | Sonnet | Coherent, contextual dialogue | 600 |
| RAG-based guest Q&A | Sonnet | Reasoning over retrieved context | 600 |
| Generate annual strategy report | Opus | Long-form, complex reasoning | 4096 |
| Autonomous multi-step agent | Opus | Extended reasoning + tool use | 2048 |
| Debug complex Python pipeline | Opus | Deep code understanding | 2048 |
| Negotiate supplier contracts | Opus | Strategic analysis of trade-offs | 2048 |

```python
# Restaurant-specific configuration
LUMIERE_TASK_MODELS = {
    # ── Haiku tasks (high volume, simple) ─────────────────────────────
    "route_query":           ("claude-haiku-4-5-20251001", 10),
    "detect_language":       ("claude-haiku-4-5-20251001", 5),
    "answer_faq":            ("claude-haiku-4-5-20251001", 150),
    "check_allergen_risk":   ("claude-haiku-4-5-20251001", 5),
    "check_scope":           ("claude-haiku-4-5-20251001", 10),
    
    # ── Sonnet tasks (standard production workloads) ───────────────────
    "wine_recommendation":   ("claude-sonnet-4-6", 400),
    "invoice_extraction":    ("claude-sonnet-4-6", 300),
    "menu_description":      ("claude-sonnet-4-6", 300),
    "anomaly_detection":     ("claude-sonnet-4-6", 500),
    "guest_chat":            ("claude-sonnet-4-6", 600),
    "rag_query":             ("claude-sonnet-4-6", 600),
    
    # ── Opus tasks (complex, low volume) ──────────────────────────────
    "strategy_report":       ("claude-opus-4-6", 4096),
    "autonomous_agent":      ("claude-opus-4-6", 2048),
    "debug_pipeline":        ("claude-opus-4-6", 2048),
}

def get_model_and_tokens(task: str) -> tuple[str, int]:
    """Get model and max_tokens for a task."""
    model, tokens = LUMIERE_TASK_MODELS.get(task, ("claude-sonnet-4-6", 600))
    return model, tokens
```

---

## 7. Evaluation-Driven Model Selection

Never select a model without measuring quality. Run an eval before deciding.

```python
from typing import Callable
import statistics

def run_model_comparison(
    eval_dataset: list[dict],
    judge_fn: Callable[[str, str], float],
    models: list[str] = None,
    repetitions: int = 1,
) -> dict:
    """
    Compare multiple models on your evaluation dataset.
    
    Args:
        eval_dataset:   List of {"input": str, "expected": str, "category": str}
        judge_fn:       Function that scores (response, expected) → float 0-1
        models:         Models to compare (default: all three)
        repetitions:    Times to run each item (for variance measurement)
    
    Returns:
        Comparison results with scores, variance, and cost estimates
    
    Usage:
        dataset = [
            {"input": "Recommend a wine for salmon", "expected": "crisp white wine..."},
            {"input": "Do you have vegan options?", "expected": "Yes, we have..."},
        ]
        results = run_model_comparison(dataset, llm_judge_score)
        print(results["winner"])  # "claude-sonnet-4-6"
        print(results["savings"]["sonnet_vs_opus"])  # "$12,000/month"
    """
    if models is None:
        models = ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-6"]
    
    results = {model: {"scores": [], "responses": []} for model in models}
    
    for item in eval_dataset:
        for model in models:
            for _ in range(repetitions):
                response = anthropic.Anthropic().messages.create(
                    model=model,
                    max_tokens=600,
                    messages=[{"role": "user", "content": item["input"]}]
                ).content[0].text
                
                score = judge_fn(response, item.get("expected", ""))
                results[model]["scores"].append(score)
                results[model]["responses"].append(response)
    
    # Compute statistics
    stats = {}
    for model in models:
        scores = results[model]["scores"]
        stats[model] = {
            "avg_score":    round(statistics.mean(scores), 3),
            "median_score": round(statistics.median(scores), 3),
            "min_score":    round(min(scores), 3),
            "std_dev":      round(statistics.stdev(scores) if len(scores) > 1 else 0, 3),
            "pass_rate":    round(sum(1 for s in scores if s >= 0.8) / len(scores), 3),
        }
    
    # Find winner
    winner = max(models, key=lambda m: stats[m]["avg_score"])
    
    # Find cheapest model meeting threshold
    QUALITY_THRESHOLD = 0.80
    affordable_winner = None
    for model in ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-6"]:
        if stats.get(model, {}).get("avg_score", 0) >= QUALITY_THRESHOLD:
            affordable_winner = model
            break
    
    return {
        "stats":              stats,
        "winner":             winner,
        "affordable_winner":  affordable_winner,
        "recommendation":     affordable_winner or winner,
        "eval_size":          len(eval_dataset),
    }


def compare_model_before_migration(
    current_model: str,
    new_model: str,
    eval_dataset: list[dict],
    judge_fn: Callable,
) -> dict:
    """
    Before migrating to a new model version, verify quality is maintained.
    
    Run this as part of your CI/CD pipeline when updating model strings.
    
    Args:
        current_model: Model currently in production
        new_model:     Model you're considering migrating to
        eval_dataset:  Evaluation dataset (minimum 50 examples)
        judge_fn:      Scoring function
    
    Returns:
        Migration recommendation: "safe_to_migrate" or "regression_detected"
    
    Regression threshold: Migration is blocked if new model scores more than
    5% lower than current model on average.
    """
    REGRESSION_THRESHOLD = 0.05
    
    current_scores = []
    new_scores = []
    
    for item in eval_dataset:
        for model, scores_list in [(current_model, current_scores), (new_model, new_scores)]:
            response = anthropic.Anthropic().messages.create(
                model=model,
                max_tokens=600,
                messages=[{"role": "user", "content": item["input"]}]
            ).content[0].text
            scores_list.append(judge_fn(response, item.get("expected", "")))
    
    current_avg = statistics.mean(current_scores)
    new_avg     = statistics.mean(new_scores)
    delta       = new_avg - current_avg
    
    safe = delta >= -REGRESSION_THRESHOLD
    
    print(f"\nMigration Analysis: {current_model} → {new_model}")
    print(f"  Current:  {current_avg:.3f}")
    print(f"  New:      {new_avg:.3f}")
    print(f"  Delta:    {delta:+.3f}")
    print(f"  Decision: {'✅ SAFE TO MIGRATE' if safe else '🔴 REGRESSION DETECTED — DO NOT MIGRATE'}")
    
    return {
        "current_model":  current_model,
        "new_model":      new_model,
        "current_avg":    current_avg,
        "new_avg":        new_avg,
        "delta":          delta,
        "decision":       "safe_to_migrate" if safe else "regression_detected",
        "recommendation": new_model if safe else current_model,
    }
```

---

## 8. Version Pinning and Migration Strategy

```python
# ════════════════════════════════════════════════════════════════
# VERSION PINNING — Always pin to specific model versions
# ════════════════════════════════════════════════════════════════

# ❌ NEVER use unpinned model names
# Model behaviour changes when Anthropic updates
model = "claude-sonnet"  # WRONG — will silently change behaviour

# ✅ ALWAYS pin to full version string
model = "claude-sonnet-4-6"  # Deterministic behaviour

# ════════════════════════════════════════════════════════════════
# CONFIGURATION FILE PATTERN
# ════════════════════════════════════════════════════════════════

# config/models.py — Single source of truth for model versions
class ModelConfig:
    """
    Central model configuration.
    
    To update a model:
    1. Change the version string here
    2. Run your eval suite: python -m pytest tests/eval/
    3. If eval passes, deploy
    4. Monitor metrics for 24h before full rollout
    
    Never update model strings without running eval first!
    """
    
    # Primary production models
    PRIMARY    = "claude-sonnet-4-6"       # Main generation tasks
    ROUTING    = "claude-haiku-4-5-20251001" # Classification/routing
    ADVANCED   = "claude-opus-4-6"         # Complex reasoning only
    
    # Compression model (for summarizing history, etc.)
    COMPRESS   = "claude-haiku-4-5-20251001"
    
    # Evaluation/judge model
    JUDGE      = "claude-sonnet-4-6"
    
    # Fallback model (used when PRIMARY is unavailable)
    FALLBACK   = "claude-haiku-4-5-20251001"
    
    @classmethod
    def get_all(cls) -> dict:
        """Return all model configurations as a dict."""
        return {k: v for k, v in vars(cls).items() 
                if not k.startswith('_') and isinstance(v, str)}

# Usage throughout codebase:
from config.models import ModelConfig

response = client.messages.create(
    model=ModelConfig.PRIMARY,  # ← Single point of change for migrations
    max_tokens=600,
    messages=messages,
)
```

### Version Migration Checklist

```python
# migration_checklist.md equivalent as code

MIGRATION_CHECKLIST = {
    "pre_migration": [
        "Run eval suite on both old and new model",
        "Check delta >= -5% on all eval categories",
        "Check cost difference and update budget",
        "Update ModelConfig version string in feature branch",
        "Notify stakeholders of planned change",
    ],
    "during_migration": [
        "Deploy to staging first",
        "Run smoke tests on staging",
        "Deploy to 10% production traffic (if A/B supported)",
        "Monitor error rates and quality scores for 4 hours",
    ],
    "post_migration": [
        "Run full eval suite against production traffic sample",
        "Confirm no quality regression in Application Insights",
        "Update ModelConfig in production branch",
        "Document migration in CHANGELOG.md",
        "Set calendar reminder to review in 30 days",
    ],
}
```

---

## 9. Environment-Based Configuration

```python
import os
from functools import lru_cache

@lru_cache(maxsize=None)
def get_model_config() -> dict:
    """
    Load model configuration from environment variables.
    
    Environment Variables:
        CLAUDE_ENV:                "production" | "staging" | "development"
        CLAUDE_PRIMARY_MODEL:     Override primary model
        CLAUDE_ROUTING_MODEL:     Override routing model
        CLAUDE_ADVANCED_MODEL:    Override advanced model
        CLAUDE_COST_MODE:         "economy" | "balanced" | "quality"
    
    Cost modes:
        economy:  Haiku everywhere (max cost reduction, lower quality)
        balanced: Haiku routing + Sonnet generation (recommended)
        quality:  Sonnet routing + Opus generation (max quality, high cost)
    
    Usage:
        # In production (Azure App Service):
        CLAUDE_ENV=production
        CLAUDE_COST_MODE=balanced
        
        # In development (local):
        CLAUDE_ENV=development
        CLAUDE_COST_MODE=economy  # Save cost while testing
    """
    env = os.getenv("CLAUDE_ENV", "development")
    cost_mode = os.getenv("CLAUDE_COST_MODE", "balanced")
    
    # Cost mode presets
    COST_MODE_PRESETS = {
        "economy": {
            "routing":    "claude-haiku-4-5-20251001",
            "generation": "claude-haiku-4-5-20251001",
            "analysis":   "claude-sonnet-4-6",
        },
        "balanced": {
            "routing":    "claude-haiku-4-5-20251001",
            "generation": "claude-sonnet-4-6",
            "analysis":   "claude-opus-4-6",
        },
        "quality": {
            "routing":    "claude-sonnet-4-6",
            "generation": "claude-sonnet-4-6",
            "analysis":   "claude-opus-4-6",
        },
    }
    
    preset = COST_MODE_PRESETS.get(cost_mode, COST_MODE_PRESETS["balanced"])
    
    return {
        "env":      env,
        "cost_mode": cost_mode,
        "routing":    os.getenv("CLAUDE_ROUTING_MODEL",    preset["routing"]),
        "generation": os.getenv("CLAUDE_PRIMARY_MODEL",    preset["generation"]),
        "analysis":   os.getenv("CLAUDE_ADVANCED_MODEL",   preset["analysis"]),
    }

# Usage:
config = get_model_config()
response = client.messages.create(
    model=config["generation"],
    max_tokens=600,
    messages=messages,
)
```

---

## 10. Junior Walkthrough — Choose a Model for Your First App

**Scenario**: "I'm building a chatbot for the restaurant. Which model should I use?"

**Step 1: What does your app actually do?**

```python
# Ask yourself:
# 1. What's the volume? (requests/day)
# 2. What's the complexity? (simple Q&A vs deep analysis)
# 3. Is latency critical? (user waiting vs background)
# 4. What's the quality bar? (must-be-right vs mostly-right)
```

**Step 2: Start with Sonnet (the safe default)**

```python
# For a restaurant chatbot: guest questions, menu info, wine recommendations
# → Sonnet is the safe default — excellent quality, reasonable cost

response = client.messages.create(
    model="claude-sonnet-4-6",  # Safe default for most tasks
    max_tokens=600,
    messages=[{"role": "user", "content": user_question}],
)
```

**Step 3: Identify repetitive simple tasks that could use Haiku**

```python
# If you find yourself doing the same simple thing many times:
# "Is this a wine question? Yes/No" → Switch to Haiku

# Haiku routing (fast + cheap):
category = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=10,
    messages=[{"role": "user", "content": f"Classify as wine/menu/booking/other: {question}"}]
).content[0].text.strip()
```

**Step 4: Calculate your monthly cost and decide**

```python
# 100 requests/day, 1,500 input + 400 output tokens
compare_models_for_workload(100, 1_500, 400)
# Haiku:  ~$2/month  ← if quality is good enough
# Sonnet: ~$16/month ← recommended for restaurant AI
# Opus:   ~$82/month ← only if Sonnet quality is measurably insufficient
```

---

## 11. Senior Patterns — Model Strategy at Scale

```python
class AdaptiveModelSelector:
    """
    Dynamically adjusts model selection based on real-time cost and quality signals.
    
    Features:
    - A/B test model versions automatically
    - Promote cheaper model if quality matches
    - Downgrade under cost pressure
    - Upgrade if quality drops
    """
    
    def __init__(self, quality_threshold: float = 0.82):
        self.quality_threshold = quality_threshold
        self._current_config = get_model_config()
        self._quality_tracker = {}  # {model: [recent_scores]}
        self._cost_tracker    = {}  # {model: [recent_costs]}
    
    def get_model(self, task_type: str) -> str:
        """Get current model for task, with possible dynamic override."""
        base_model = self._current_config.get(
            "generation" if task_type not in ("routing", "analysis") else task_type,
            "claude-sonnet-4-6"
        )
        
        # Check if we should try the cheaper alternative
        if self._can_try_cheaper(base_model):
            cheaper = self._get_cheaper_alternative(base_model)
            if cheaper:
                return cheaper
        
        return base_model
    
    def record_quality(self, model: str, score: float):
        self._quality_tracker.setdefault(model, []).append(score)
        # Keep last 100 scores
        self._quality_tracker[model] = self._quality_tracker[model][-100:]
    
    def _can_try_cheaper(self, model: str) -> bool:
        """Check if current quality headroom allows trying a cheaper model."""
        scores = self._quality_tracker.get(model, [])
        if len(scores) < 20:
            return False  # Not enough data
        avg = sum(scores[-20:]) / 20
        # If we're consistently scoring 10%+ above threshold, try cheaper
        return avg > self.quality_threshold + 0.10
    
    def _get_cheaper_alternative(self, model: str) -> str | None:
        alternatives = {
            "claude-opus-4-6":   "claude-sonnet-4-6",
            "claude-sonnet-4-6": "claude-haiku-4-5-20251001",
        }
        return alternatives.get(model)
```

---

## 12. Tips, Tricks, and Gotchas

### Tips

1. **Sonnet is the right default** — not Haiku (risks quality), not Opus (risks cost). Start with Sonnet, then optimize.
2. **Measure before downgrading** — run your eval dataset with Haiku before assuming it can replace Sonnet for a task
3. **Cost mode via env var** — use `CLAUDE_COST_MODE=economy` in dev/staging to slash costs during testing
4. **Haiku for pre/post processing** — even if the main task uses Sonnet, use Haiku for extraction, formatting, and validation steps

### Tricks

5. **Set `max_tokens` correctly per model** — Haiku with `max_tokens=5` is extremely fast; Sonnet with `max_tokens=10` for classification is also fast and avoids paying for output you don't need
6. **Cascade confidence check** — call Haiku with `confidence` in the output schema; only escalate to Sonnet if confidence < 0.90
7. **Per-task model configuration** — storing models in a config dict + env vars allows changing model for a single task type via deployment, no code change needed

### Gotchas

8. **"claude-sonnet" (without version) is not a valid model string** — it will return a 404 error. Always use the full version: `claude-sonnet-4-6`
9. **Opus is not always better** — for tasks with clear instructions and simple outputs (FAQ answers, field extraction), Haiku can match or exceed Opus accuracy
10. **Don't assume model scores correlate linearly with cost** — Haiku is not 19× worse than Opus; for many tasks it's within 5-10% quality
11. **Token limits are the same across all models** — all current Claude models support 200K input; don't use Haiku assuming it has a smaller context

---

## 13. Quick Reference Cheatsheet

```python
# ═══════════════════════════════════════════════════════════════
# MODEL SELECTION QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════

# 1. MODEL STRINGS (always use full version string)
HAIKU  = "claude-haiku-4-5-20251001"   # Fast, cheap, simple tasks
SONNET = "claude-sonnet-4-6"            # Default, balanced
OPUS   = "claude-opus-4-6"             # Complex reasoning only

# 2. PRICING (approximate 2026, $/million tokens)
# Haiku:  $0.80 input / $4.00 output
# Sonnet: $3.00 input / $15.00 output
# Opus:   $15.00 input / $75.00 output

# 3. DEFAULT SELECTION RULE
# Classification/routing/simple extraction → Haiku
# Standard Q&A/RAG/generation/code        → Sonnet (DEFAULT)
# Complex agents/strategic analysis       → Opus (only if measured need)

# 4. COST ESTIMATE
def monthly_cost(reqs_per_day, in_tokens, out_tokens, model=SONNET):
    p = {HAIKU: (0.80, 4.00), SONNET: (3.00, 15.00), OPUS: (15.00, 75.00)}
    ip, op = p[model]
    return round(reqs_per_day * 30 * ((in_tokens/1e6*ip) + (out_tokens/1e6*op)), 2)

# 5. CONFIGURATION PATTERN
TASK_MODELS = {
    "classify_intent":     HAIKU,
    "rag_answer":          SONNET,
    "strategic_analysis":  OPUS,
}
model = TASK_MODELS.get(task, SONNET)

# 6. CASCADE PATTERN
result = haiku_call(prompt)
if result.confidence < 0.90:
    result = sonnet_call(prompt)   # Escalate on low confidence

# 7. VERSION PINNING
# ❌ "claude-sonnet"          (unpinned — behaviour changes silently)
# ✅ "claude-sonnet-4-6"      (pinned — deterministic)

# 8. ENV-BASED CONFIG
model = os.getenv("CLAUDE_PRIMARY_MODEL", "claude-sonnet-4-6")

# 9. MIGRATION GATE
# Only migrate model version after: eval_delta >= -0.05 (no more than 5% quality drop)

# 10. HAIKU FAST PATHS (where Haiku excels)
# max_tokens=5:    yes/no, single label
# max_tokens=10:   category classification
# max_tokens=20:   short extraction (date, number, name)
# max_tokens=150:  FAQ answer
# max_tokens=300:  short explanation
```
