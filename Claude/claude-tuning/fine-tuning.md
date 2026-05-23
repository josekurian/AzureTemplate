# fine-tuning.md — When and How to Fine-Tune vs Prompt-Engineer

> **Purpose**: Decision framework for choosing between prompt engineering, RAG, fine-tuning, and training from scratch. Covers the full evaluation-driven process for knowing when to move up the stack, with Azure OpenAI fine-tuning specifics, dataset preparation, and performance comparison.  
> **Owner**: jose@hybridgenai.com | **Updated**: 2026-05-22  
> **Applies to**: Claude API (prompt engineering + RAG only), Azure OpenAI (fine-tuning), Open models (Llama, Mistral)

---

## Navigation

1. [The Build Hierarchy](#1-the-build-hierarchy)
2. [Decision Framework](#2-decision-framework)
3. [When Fine-Tuning IS the Right Answer](#3-when-fine-tuning-is-the-right-answer)
4. [Stage 1: Prompt Engineering Deep Dive](#4-stage-1-prompt-engineering-deep-dive)
5. [Stage 2: RAG Deep Dive](#5-stage-2-rag-deep-dive)
6. [Stage 3: Fine-Tuning with Azure OpenAI](#6-stage-3-fine-tuning-with-azure-openai)
7. [Dataset Preparation and Quality](#7-dataset-preparation-and-quality)
8. [Training Configuration and Cost](#8-training-configuration-and-cost)
9. [Evaluating Fine-Tune vs Prompt Performance](#9-evaluating-fine-tune-vs-prompt-performance)
10. [Deployment and A/B Testing](#10-deployment-and-ab-testing)
11. [Hybrid Architecture: Claude + Fine-tuned Model](#11-hybrid-architecture-claude--fine-tuned-model)
12. [Restaurant-Specific Guidance](#12-restaurant-specific-guidance)
13. [Junior Developer Walkthrough](#13-junior-developer-walkthrough)
14. [Senior Developer Patterns](#14-senior-developer-patterns)
15. [Tips, Tricks, and Gotchas](#15-tips-tricks-and-gotchas)
16. [Quick Reference Cheatsheet](#16-quick-reference-cheatsheet)

---

## Who This Is For

**Juniors**: Read sections 1, 2, 4, 13 — understand when NOT to fine-tune (most of the time).  
**Seniors**: Jump to sections 6, 7, 8, 9, 11 — fine-tuning implementation and evaluation.  
**Everyone**: Section 2 (decision framework) and section 15 (gotchas) before any fine-tuning decision.

---

## 1. The Build Hierarchy

Always start at the lowest level and only advance if evaluation proves insufficient quality.

```
                ┌──────────────────────────────────────────────────────┐
Level 4         │  Train from scratch                                  │
                │  Cost: $$$$$  Time: months  Data: millions examples  │
                │  When: You need capabilities no existing model has    │
                │  Reality: Almost never right for enterprise apps      │
                └──────────────────────────────────────────────────────┘
                           ▲  Only if Level 3 insufficient
                ┌──────────────────────────────────────────────────────┐
Level 3         │  Fine-tuning                                         │
                │  Cost: $$$  Time: days  Data: 50-10,000 examples     │
                │  When: Style, format, or domain is extremely specific │
                │  Models: Azure OpenAI (GPT-4o), Llama, Mistral       │
                │  NOT Claude (not fine-tunable via API as of 2026)     │
                └──────────────────────────────────────────────────────┘
                           ▲  Only if Level 2 insufficient
                ┌──────────────────────────────────────────────────────┐
Level 2         │  RAG (Retrieval-Augmented Generation)                │
                │  Cost: $$  Time: days  Data: any documents           │
                │  When: Model lacks domain knowledge                   │
                │  Best for: Fresh data, proprietary knowledge bases    │
                └──────────────────────────────────────────────────────┘
                           ▲  Only if Level 1 insufficient
                ┌──────────────────────────────────────────────────────┐
Level 1         │  Prompt Engineering                                  │
                │  Cost: $  Time: hours  Data: zero                    │
                │  When: First attempt, always                         │
                │  Models: Claude Sonnet/Opus with good prompts        │
                └──────────────────────────────────────────────────────┘
```

**The Golden Rule**: Start at Level 1. Only advance to Level 2 after measuring Level 1's inadequacy. Only advance to Level 3 after measuring Level 2's inadequacy.

Advancing prematurely costs money, time, and creates maintenance burden — a fine-tuned model needs re-training whenever domain knowledge changes, while RAG updates instantly.

---

## 2. Decision Framework

Work through this table top-to-bottom. Stop at the first row that resolves your situation.

| Question to Answer | Measured Evidence | Recommendation |
|-------------------|-------------------|----------------|
| Does the model lack factual domain knowledge? | Eval score <0.70 on domain-specific questions | Add RAG (Level 2) |
| Does the model know the content but produce wrong format? | JSON parse failure rate >2% | Fix prompts — be explicit about format |
| Does the model know content + format but style is wrong? | Human eval score <3.5/5 on tone | Add few-shot examples (5-10) to system prompt |
| Are you paying for huge prompts (>8K tokens) on every request? | Cost analysis shows >60% of tokens are static | Consider fine-tuning to compress knowledge |
| Do you have 100+ labeled examples and a labeled eval set? | Annotation complete | Fine-tuning is feasible |
| Has RAG + prompt engineering been measured at <0.80 quality? | Eval score <0.80 consistently | Fine-tuning may be justified |
| Are you at 100M+ requests/month? | Usage metrics | Cost analysis needed — fine-tuned small model may win |

### Decision Flowchart

```
Start here: What's the quality problem?
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   Wrong          Wrong        Wrong
   facts          format        tone
       │            │            │
    Add RAG    Fix prompt    Add few-shot
   (Level 2)   (explicit     examples
               schema)       (5-10 in
                              system prompt)
                    │
          Still failing at ≥0.80?
                    │
              YES   │   NO
               │    │    │
         Annotate   │  Done ✅
         examples   │
               │
         ≥50 examples available?
               │
          YES  │   NO
           │   │    │
       Try    │  Annotate
     fine-    │  more first
     tuning   │
           │
      Run A/B test:
      fine-tuned vs RAG+prompt
           │
      Improvement ≥10%?
           │
      YES  │   NO
       │   │    │
    Deploy │  Stay with
    fine-  │  RAG+prompt
    tuned  │
```

---

## 3. When Fine-Tuning IS the Right Answer

Fine-tuning is justified when ALL of the following are true:

### Justified Scenarios

**Format compliance at scale**: Your application calls the model 1M+ times/month and requires a specific JSON schema. Every parse failure costs downstream processing. Haiku gets it right 97% of the time with prompting but you need 99.9%. Fine-tuning on 500 examples of perfect JSON outputs can close this gap.

**Style/tone at extreme specificity**: Your brand voice is highly specific (e.g., Michelin-star sommelier prose), few-shot examples consume too much context (>3K tokens per request), and you're running high volume. Fine-tuning "bakes" the style in so your prompts can be short.

**Latency with quality requirements**: You need GPT-3.5 speed with GPT-4 quality for a specific, narrow task. A fine-tuned GPT-3.5 can match GPT-4 on a specific narrow task with sufficient training data.

**Proprietary vocabulary**: The model consistently confuses your product names, internal codes, or domain acronyms despite RAG. Fine-tuning on 200+ examples teaches the vocabulary.

**Cost at extreme scale (100M+ calls/month)**: A fine-tuned GPT-3.5-turbo (cheaper + faster) that matches GPT-4 quality on your specific task saves 90% of LLM costs.

### NOT Justified Scenarios

| Situation | Better Approach |
|-----------|----------------|
| Knowledge is changing frequently (menus, prices, policies) | RAG — updates instantly |
| You have <50 labeled examples | More prompt engineering first |
| Problem is solvable with better prompts (not tried yet) | Prompt engineering |
| You need general reasoning ability | Larger model + better prompts |
| Budget for training and evaluation is not approved | Wait |

### Important Note on Claude

**As of 2026, Claude models are not fine-tuneable via the Anthropic API.** Claude is used exclusively through prompt engineering and RAG.

If your evaluation proves fine-tuning is needed, use:
- **Azure OpenAI**: GPT-4o fine-tuning (best quality, enterprise support)
- **Azure AI Studio**: Llama 3.1 fine-tuning (open weights, portable)
- **Hugging Face + Azure ML**: Mistral, Llama (full control)

Typical architecture for applications that need fine-tuning:
```
User Request
     ↓
Claude (Sonnet) ─ complex reasoning, safety, conversation
     +
Fine-tuned GPT-4o mini ─ specific extraction, format compliance, style
```

---

## 4. Stage 1: Prompt Engineering Deep Dive

Before concluding that prompt engineering is insufficient, verify you have tried all techniques:

### Techniques Checklist

```python
# ── Technique 1: Zero-shot (baseline) ───────────────────────────────────────
BASELINE_PROMPT = """Extract the wine details from this label.
Return JSON: {"producer": str, "vintage": int, "appellation": str, "varietal": str}

Label text: {label_text}"""

# ── Technique 2: Few-shot examples ──────────────────────────────────────────
FEW_SHOT_PROMPT = """Extract wine details from labels. Return JSON only.

Example 1:
Label: "Château Margaux 2015 Margaux, Bordeaux"
Output: {"producer": "Château Margaux", "vintage": 2015, "appellation": "Margaux", "varietal": "Bordeaux Blend"}

Example 2:
Label: "Domaine Leflaive Puligny-Montrachet 1er Cru Les Pucelles 2019"
Output: {"producer": "Domaine Leflaive", "vintage": 2019, "appellation": "Puligny-Montrachet 1er Cru", "varietal": "Chardonnay"}

Now extract from:
Label: {label_text}
Output:"""

# ── Technique 3: Chain-of-thought + structured output ───────────────────────
COT_PROMPT = """Extract wine details from this label. Think step by step.

1. First, identify the producer name (usually largest text or before the appellation)
2. Find the vintage year (4-digit number between 1900-2030)
3. Identify the appellation (geographical designation)
4. Determine the varietal if mentioned

After thinking, output ONLY this JSON:
{"producer": "...", "vintage": YYYY, "appellation": "...", "varietal": "..."}

Label: {label_text}"""

# ── Technique 4: Explicit schema with constraints ────────────────────────────
SCHEMA_PROMPT = """You are a wine data extraction expert. Extract structured data from wine labels.

RULES:
- vintage must be an integer between 1900 and 2030
- If vintage is not found, use null (not 0, not "unknown")
- producer should be the winery/domaine/château name only (not including appellation)
- appellation is the geographical designation (e.g., "Pomerol", "Napa Valley Cabernet Sauvignon")
- varietal is the grape variety (e.g., "Pinot Noir", "Chardonnay") or "Bordeaux Blend" for blends
- Return ONLY the JSON object — no preamble, no explanation

Output schema:
{
  "producer": string | null,
  "vintage": integer | null,
  "appellation": string | null,
  "varietal": string | null,
  "confidence": float (0.0-1.0)
}

Label: {label_text}"""

# ── Measuring prompt effectiveness ──────────────────────────────────────────
def evaluate_prompt_variants(
    prompts: dict[str, str],
    eval_dataset: list[dict],
    model: str = "claude-sonnet-4-6",
) -> dict:
    """
    Measure each prompt variant against a labeled dataset.
    Run this before concluding prompt engineering is insufficient.
    
    Returns: {prompt_name: {"parse_rate": float, "field_accuracy": float, "avg_score": float}}
    """
    import anthropic
    client = anthropic.Anthropic()
    results = {}
    
    for prompt_name, prompt_template in prompts.items():
        parse_successes = 0
        field_scores = []
        
        for item in eval_dataset:
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=300,
                    messages=[{
                        "role": "user",
                        "content": prompt_template.format(label_text=item["input"]),
                    }],
                )
                
                text = response.content[0].text
                parsed = json.loads(text)
                parse_successes += 1
                
                # Score each field
                score = 0
                expected = item["expected"]
                for field in ["producer", "vintage", "appellation", "varietal"]:
                    if str(parsed.get(field, "")).lower() == str(expected.get(field, "")).lower():
                        score += 0.25
                
                field_scores.append(score)
            
            except (json.JSONDecodeError, Exception):
                field_scores.append(0.0)
        
        results[prompt_name] = {
            "parse_rate": parse_successes / len(eval_dataset),
            "avg_field_accuracy": sum(field_scores) / len(field_scores),
            "n_examples": len(eval_dataset),
        }
    
    return results
```

### Measuring Prompt Quality — The Gate

```python
PROMPT_QUALITY_THRESHOLD = 0.80  # Minimum to consider prompt engineering sufficient
PARSE_RATE_THRESHOLD = 0.98      # Minimum JSON parse success rate

def should_advance_to_rag(
    prompt_eval_results: dict,
    quality_issues: list[str],
) -> tuple[bool, str]:
    """
    Determine if RAG is needed based on prompt evaluation.
    
    Returns (should_advance, reason)
    
    Advance to RAG if:
    1. Quality is below threshold AND the failure mode is missing domain knowledge
    
    Do NOT advance to RAG if:
    - Quality is below threshold due to format/tone (fix prompt instead)
    - You haven't tried few-shot examples yet
    """
    best_result = max(prompt_eval_results.values(), key=lambda r: r["avg_field_accuracy"])
    
    if best_result["avg_field_accuracy"] >= PROMPT_QUALITY_THRESHOLD:
        return False, f"Prompt quality sufficient ({best_result['avg_field_accuracy']:.2f} ≥ {PROMPT_QUALITY_THRESHOLD})"
    
    knowledge_failures = [q for q in quality_issues if "unknown" in q.lower() or "not found" in q.lower() or "missing" in q.lower()]
    
    if knowledge_failures:
        return True, f"Quality {best_result['avg_field_accuracy']:.2f} < {PROMPT_QUALITY_THRESHOLD} due to missing knowledge: {knowledge_failures[:3]}"
    
    return False, f"Quality {best_result['avg_field_accuracy']:.2f} < {PROMPT_QUALITY_THRESHOLD} — fix format/tone issues before considering RAG"
```

---

## 5. Stage 2: RAG Deep Dive

Before concluding RAG is insufficient, verify these RAG optimizations have been tried:

### RAG Optimization Checklist

```python
# ── Chunking strategy (most impact) ─────────────────────────────────────────
# Bad: fixed-size chunks (breaks semantic units)
# Good: semantic chunking (one section/paragraph per chunk)
# Better: hierarchical chunks (large for recall, small for precision)

# ── Retrieval strategy ───────────────────────────────────────────────────────
# Bad: pure vector search (misses exact keyword matches)
# Good: hybrid search = BM25 (keyword) + vector (semantic) + re-ranker

# ── Re-ranking (biggest quality improvement) ─────────────────────────────────
# Use Azure AI Search semantic ranker or a cross-encoder to re-rank top-k results
# This often improves quality by 15-20 points without any training

# ── Context construction ─────────────────────────────────────────────────────
# Bad: dump all retrieved chunks into context
# Good: format chunks with source attribution and relevance score
# Best: pick top-3 chunks + instruct Claude to cite sources

def rag_quality_gate(
    rag_eval_results: dict,
    baseline_prompt_score: float,
) -> tuple[bool, str]:
    """
    Determine if fine-tuning is needed after RAG.
    
    Advance to fine-tuning only if:
    1. RAG quality < 0.80 AND
    2. Failure mode is style/format (not knowledge) AND
    3. You have ≥ 50 labeled training examples
    """
    rag_score = rag_eval_results.get("avg_score", 0)
    improvement = rag_score - baseline_prompt_score
    
    if rag_score >= 0.80:
        return False, f"RAG quality sufficient ({rag_score:.2f}). Fine-tuning not needed."
    
    if improvement < 0.05:
        return False, f"RAG only improved by {improvement:.2f} — the problem may be format/style, not knowledge. Try better prompts."
    
    return True, f"RAG quality ({rag_score:.2f}) still below target (0.80). Fine-tuning may help if you have enough training data."
```

---

## 6. Stage 3: Fine-Tuning with Azure OpenAI

### Prerequisites

```
Before starting fine-tuning:
✅ [ ] Prompt engineering tried and measured (quality <0.80)
✅ [ ] RAG tried and measured (quality still <0.80)
✅ [ ] At least 50 high-quality labeled examples (200+ recommended)
✅ [ ] 20+ labeled evaluation examples (held-out, never used for training)
✅ [ ] Budget approved: training cost + ongoing inference cost comparison
✅ [ ] Azure OpenAI resource provisioned (or Llama via Azure AI Studio)
✅ [ ] Rollback plan: fall back to RAG + Sonnet if fine-tuned model underperforms
```

### Azure OpenAI Fine-Tuning Process

```python
from openai import AzureOpenAI
import json
import time

# Initialize Azure OpenAI client for fine-tuning
ft_client = AzureOpenAI(
    azure_endpoint="https://lumiere-openai.openai.azure.com/",
    api_key="YOUR_AZURE_OPENAI_KEY",
    api_version="2024-08-01-preview",
)


# ── Step 1: Prepare training data ───────────────────────────────────────────
def prepare_fine_tuning_dataset(examples: list[dict], output_file: str):
    """
    Prepare training data in OpenAI fine-tuning format.
    
    Each example must have:
    - input: the user message
    - ideal_output: the ideal model response
    
    File format: JSONL (one JSON object per line)
    Minimum recommended: 50 examples
    Optimal: 200-1000 examples
    Maximum: No hard limit, but 10,000+ rarely adds quality
    
    Quality > Quantity: 50 perfect examples beat 500 mediocre ones.
    """
    with open(output_file, "w") as f:
        for example in examples:
            record = {
                "messages": [
                    {
                        "role": "system",
                        "content": RESTAURANT_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": example["input"],
                    },
                    {
                        "role": "assistant",
                        "content": example["ideal_output"],
                    },
                ]
            }
            f.write(json.dumps(record) + "\n")
    
    print(f"✅ Wrote {len(examples)} training examples to {output_file}")
    validate_fine_tuning_dataset(output_file)


def validate_fine_tuning_dataset(file_path: str):
    """
    Validate dataset format before submitting.
    Catches common errors: missing roles, empty content, too-short responses.
    """
    issues = []
    
    with open(file_path) as f:
        for i, line in enumerate(f):
            try:
                record = json.loads(line.strip())
            except json.JSONDecodeError as e:
                issues.append(f"Line {i+1}: Invalid JSON — {e}")
                continue
            
            messages = record.get("messages", [])
            roles = [m.get("role") for m in messages]
            
            if roles != ["system", "user", "assistant"]:
                issues.append(f"Line {i+1}: Expected [system, user, assistant] roles, got {roles}")
            
            for msg in messages:
                if not msg.get("content", "").strip():
                    issues.append(f"Line {i+1}: Empty content for role '{msg.get('role')}'")
            
            assistant_content = next((m["content"] for m in messages if m["role"] == "assistant"), "")
            if len(assistant_content) < 10:
                issues.append(f"Line {i+1}: Very short assistant response ({len(assistant_content)} chars) — may harm training quality")
    
    if issues:
        print(f"⚠️  Dataset validation issues ({len(issues)}):")
        for issue in issues[:10]:
            print(f"   {issue}")
    else:
        print("✅ Dataset validation passed")
    
    return len(issues) == 0
```

### Training Examples for Lumière

```python
# Wine pairing training examples for Lumière
WINE_PAIRING_EXAMPLES = [
    {
        "input": "We're having the aged Wagyu beef as our main course. What wine would you recommend?",
        "ideal_output": "For our aged Wagyu, I'd suggest the Château Léoville-Barton 2018 Saint-Julien — its structured tannins and cassis notes beautifully complement the rich marbling. At £145, it's exceptional value for a second-growth Bordeaux. Alternatively, our Domaine de la Romanée-Conti Nuits-Saint-Georges 2016 at £380 offers a more Burgundian interpretation that highlights the beef's umami complexity.",
    },
    {
        "input": "My guest is vegetarian and we want a wine that works with both the mushroom risotto and the roasted cauliflower.",
        "ideal_output": "A white Burgundy would be my first recommendation — specifically our Domaine Leflaive Puligny-Montrachet 2019 at £185. Its rich texture and mineral edge pair beautifully with the earthy mushrooms, while its acidity cuts through the cauliflower's sweetness. If you'd prefer red, the Chambolle-Musigny 2017 from Roumier at £220 is elegant enough not to overpower either dish.",
    },
    {
        "input": "We're celebrating a 25th anniversary. What's your most special bottle?",
        "ideal_output": "For a 25th anniversary, I'd be honoured to present our 1999 Pétrus from the cellar — a profound Pomerol that has been drinking beautifully this year. At £3,200, it's an extraordinary expression of Merlot that few get to experience. Should you prefer something more approachable, our Opus One 2001 at £850 offers a beautiful bridge between Napa Valley structure and Bordeaux elegance — the 2001 vintage is particularly meaningful for a milestone year.",
    },
    # ... 47+ more examples
]


# Menu description training examples
MENU_DESCRIPTION_EXAMPLES = [
    {
        "input": "Rewrite this description with more elegant language: 'Beef tenderloin with mushroom sauce and vegetables'",
        "ideal_output": "Seared Beef Fillet\nA prime cut of 28-day dry-aged British fillet, cooked precisely to temperature, accompanied by a woodland mushroom duxelles, glazed root vegetables, and a port wine reduction that honours the beef's inherent depth.",
    },
    {
        "input": "Create a description for: Pan-fried sea bass, fennel, saffron cream",
        "ideal_output": "Wild Sea Bass\nDelicate fillets of line-caught sea bass, skin crisped to perfection, resting on a slow-braised fennel fondant infused with star anise. Finished with a saffron beurre blanc that brings the warmth of the Mediterranean to your table.",
    },
]


# Complete dataset combining all task types
FINE_TUNING_DATASET = WINE_PAIRING_EXAMPLES + MENU_DESCRIPTION_EXAMPLES
```

### Submitting and Managing the Fine-Tuning Job

```python
def submit_fine_tuning_job(
    training_file: str,
    validation_file: str = None,
    model: str = "gpt-4o-mini-2024-07-18",   # Cost-effective base model
    n_epochs: int = 3,                         # Default: 3. Range: 1-10
    batch_size: str = "auto",                  # "auto" or integer
    learning_rate_multiplier: float = 1.0,     # Default: 1.0. Range: 0.1-10.0
    suffix: str = "lumiere-v1",               # Your identifier for the fine-tuned model
) -> str:
    """
    Submit a fine-tuning job to Azure OpenAI.
    
    Hyperparameter guidance:
        n_epochs=3:     Good starting point. Increase to 5 if quality is low.
                        Reduce to 1-2 if you see overfitting on eval set.
        learning_rate_multiplier=1.0:  Start here. Reduce to 0.1-0.5 for subtle style
                                       adjustments. Increase to 2-5 for strong format training.
        batch_size="auto":  Let the API decide. Manual override only if you know what you're doing.
    
    Estimated cost (2026):
        GPT-4o mini: ~$3 per 1M training tokens
        GPT-4o:      ~$25 per 1M training tokens
    
    Typical training file: 500 examples × 500 tokens/example = 250K tokens
    Cost: 250K × 3 epochs = 750K tokens × $3/1M = ~$2.25 for GPT-4o mini
    """
    # Upload training file
    with open(training_file) as f:
        training_response = ft_client.files.create(
            file=f,
            purpose="fine-tune",
        )
    training_file_id = training_response.id
    print(f"Training file uploaded: {training_file_id}")
    
    # Upload validation file if provided
    validation_file_id = None
    if validation_file:
        with open(validation_file) as f:
            validation_response = ft_client.files.create(
                file=f,
                purpose="fine-tune",
            )
        validation_file_id = validation_response.id
        print(f"Validation file uploaded: {validation_file_id}")
    
    # Create fine-tuning job
    hyperparameters = {
        "n_epochs": n_epochs,
        "learning_rate_multiplier": learning_rate_multiplier,
    }
    if batch_size != "auto":
        hyperparameters["batch_size"] = batch_size
    
    job = ft_client.fine_tuning.jobs.create(
        training_file=training_file_id,
        validation_file=validation_file_id,
        model=model,
        hyperparameters=hyperparameters,
        suffix=suffix,
    )
    
    print(f"✅ Fine-tuning job submitted: {job.id}")
    print(f"   Status: {job.status}")
    print(f"   Model: {model} → {suffix}")
    return job.id


def poll_fine_tuning_job(job_id: str, poll_interval: int = 60) -> dict:
    """Poll fine-tuning job until completion."""
    while True:
        job = ft_client.fine_tuning.jobs.retrieve(job_id)
        
        print(f"Status: {job.status} | "
              f"Trained tokens: {job.trained_tokens or 'N/A'} | "
              f"Fine-tuned model: {job.fine_tuned_model or 'pending'}")
        
        if job.status in ("succeeded", "failed", "cancelled"):
            if job.status == "succeeded":
                print(f"✅ Fine-tuned model ready: {job.fine_tuned_model}")
            else:
                print(f"❌ Fine-tuning {job.status}")
            return {
                "status": job.status,
                "fine_tuned_model": job.fine_tuned_model,
                "trained_tokens": job.trained_tokens,
            }
        
        time.sleep(poll_interval)
```

---

## 7. Dataset Preparation and Quality

### Quality Guidelines

The single most important factor in fine-tuning quality is dataset quality, not quantity.

```python
from dataclasses import dataclass

@dataclass
class DatasetQualityMetrics:
    total_examples: int
    avg_input_tokens: float
    avg_output_tokens: float
    min_output_length: int
    max_output_length: int
    consistency_score: float   # How consistent are responses to similar inputs?
    coverage_score: float      # Does dataset cover all task subtypes?


# Quality standards for Lumière dataset
DATASET_QUALITY_STANDARDS = {
    "min_examples": 50,              # Absolute minimum
    "recommended_examples": 200,     # For reliable quality
    "min_output_length_chars": 20,   # Avoid trivially short responses
    "max_output_length_chars": 2000, # Avoid overly long (affects cost)
    "min_consistency_score": 0.80,   # Human raters should agree 80%+ on quality
    "task_coverage": {
        "wine_pairing": 0.30,        # 30% of dataset should cover this
        "menu_descriptions": 0.25,
        "dietary_enquiries": 0.20,
        "reservation_assistance": 0.15,
        "general_restaurant_info": 0.10,
    },
}


def analyse_dataset_quality(file_path: str) -> DatasetQualityMetrics:
    """Analyse a fine-tuning dataset for quality issues."""
    import tiktoken
    enc = tiktoken.encoding_for_model("gpt-4")
    
    examples = []
    with open(file_path) as f:
        for line in f:
            record = json.loads(line.strip())
            messages = record["messages"]
            user_content = next(m["content"] for m in messages if m["role"] == "user")
            assistant_content = next(m["content"] for m in messages if m["role"] == "assistant")
            
            examples.append({
                "input_tokens": len(enc.encode(user_content)),
                "output_tokens": len(enc.encode(assistant_content)),
                "output_chars": len(assistant_content),
            })
    
    output_chars = [e["output_chars"] for e in examples]
    
    return DatasetQualityMetrics(
        total_examples=len(examples),
        avg_input_tokens=sum(e["input_tokens"] for e in examples) / len(examples),
        avg_output_tokens=sum(e["output_tokens"] for e in examples) / len(examples),
        min_output_length=min(output_chars),
        max_output_length=max(output_chars),
        consistency_score=0.0,  # Requires human eval
        coverage_score=0.0,     # Requires manual categorization
    )


def print_dataset_analysis(metrics: DatasetQualityMetrics):
    """Print dataset analysis with recommendations."""
    print(f"\n{'='*50}")
    print(f"Dataset Analysis")
    print(f"{'='*50}")
    print(f"Total examples:      {metrics.total_examples}")
    print(f"Avg input tokens:    {metrics.avg_input_tokens:.0f}")
    print(f"Avg output tokens:   {metrics.avg_output_tokens:.0f}")
    print(f"Output length range: {metrics.min_output_length} - {metrics.max_output_length} chars")
    
    if metrics.total_examples < 50:
        print(f"\n⚠️  WARNING: Only {metrics.total_examples} examples. Minimum is 50. Collect more data.")
    elif metrics.total_examples < 200:
        print(f"\n⚠️  Note: {metrics.total_examples} examples is workable but 200+ is recommended.")
    else:
        print(f"\n✅ Example count looks good ({metrics.total_examples})")
    
    if metrics.min_output_length < 20:
        print(f"⚠️  Some outputs are very short ({metrics.min_output_length} chars). Check for empty/poor quality examples.")
```

### Creating High-Quality Training Data

```python
def curate_from_production_logs(
    conversation_logs: list[dict],
    quality_threshold: float = 0.85,
    human_reviewer_emails: list[str] = None,
) -> list[dict]:
    """
    Extract high-quality training examples from production conversations.
    
    This is the most efficient way to build a training dataset:
    1. Run Claude in production
    2. Log all conversations
    3. Use Claude to score them (LLM-as-judge)
    4. Human review the top scoring ones
    5. Use these as training data
    
    Steps 1-4 are automated. Step 5 requires human time.
    """
    import anthropic
    client = anthropic.Anthropic()
    
    curated = []
    
    JUDGE_PROMPT = """Rate this restaurant AI response on a scale of 0.0-1.0.

Criteria:
- Accurate information about wine/food (0-0.3)
- Tone: elegant, warm, Michelin-star appropriate (0-0.3)
- Specific recommendations (not generic) (0-0.2)
- Correct safety disclaimers where needed (0-0.1)
- Appropriate length (not too short or too long) (0-0.1)

User question: {user_message}
AI response: {ai_response}

Return only a JSON: {{"score": 0.XX, "reason": "brief note"}}"""
    
    for log in conversation_logs:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Cheap judge for first pass
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": JUDGE_PROMPT.format(
                    user_message=log["user_message"],
                    ai_response=log["ai_response"],
                ),
            }],
        )
        
        try:
            judgment = json.loads(response.content[0].text)
            score = judgment.get("score", 0)
            
            if score >= quality_threshold:
                curated.append({
                    "input": log["user_message"],
                    "ideal_output": log["ai_response"],
                    "auto_score": score,
                    "auto_reason": judgment.get("reason", ""),
                    "needs_human_review": score < 0.95,  # Human verify borderline cases
                })
        except json.JSONDecodeError:
            pass
    
    print(f"Curated {len(curated)} examples from {len(conversation_logs)} logs "
          f"(threshold: {quality_threshold})")
    
    return curated
```

---

## 8. Training Configuration and Cost

### Cost Estimation

```python
def estimate_fine_tuning_cost(
    n_examples: int,
    avg_tokens_per_example: int,
    n_epochs: int = 3,
    model: str = "gpt-4o-mini-2024-07-18",
) -> dict:
    """
    Estimate Azure OpenAI fine-tuning cost.
    
    Formula: n_examples × avg_tokens × n_epochs × price_per_token
    
    2026 Azure OpenAI pricing (indicative):
        gpt-4o-mini fine-tuning:  $0.003 per 1K training tokens
        gpt-4o fine-tuning:       $0.025 per 1K training tokens
        gpt-3.5-turbo fine-tuning: $0.008 per 1K training tokens
    
    Inference cost (fine-tuned, per 1K tokens):
        gpt-4o-mini fine-tuned:  $0.0003 input + $0.0012 output
        gpt-4o fine-tuned:       $0.00375 input + $0.015 output
    """
    TRAINING_COST_PER_1K = {
        "gpt-4o-mini-2024-07-18": 0.003,
        "gpt-4o-2024-08-06":      0.025,
        "gpt-35-turbo":           0.008,
    }
    
    total_training_tokens = n_examples * avg_tokens_per_example * n_epochs
    training_cost = total_training_tokens / 1000 * TRAINING_COST_PER_1K.get(model, 0.003)
    
    return {
        "total_training_tokens": total_training_tokens,
        "training_cost_usd": round(training_cost, 4),
        "breakeven_monthly_calls": None,  # Calculated separately
        "model": model,
        "n_epochs": n_epochs,
    }


# Example calculation: Lumière wine pairing fine-tuning
example_cost = estimate_fine_tuning_cost(
    n_examples=500,
    avg_tokens_per_example=400,  # System prompt + user + assistant
    n_epochs=3,
    model="gpt-4o-mini-2024-07-18",
)
# Result: 500 × 400 × 3 = 600K tokens × $0.003/1K = $1.80 training cost
```

---

## 9. Evaluating Fine-Tune vs Prompt Performance

### Comprehensive Evaluation

```python
from dataclasses import dataclass
from statistics import mean, stdev

@dataclass
class ModelEvalResults:
    model_id: str
    approach: str              # "prompt_engineering", "rag", "fine_tuned"
    avg_score: float
    std_dev: float
    min_score: float
    parse_rate: float          # % that produced valid JSON (for extraction tasks)
    avg_latency_ms: float
    avg_cost_per_call: float


def compare_approaches(eval_dataset: list, fine_tuned_model_id: str = None) -> dict:
    """
    Compare prompt-engineering vs RAG vs fine-tuned model performance.
    
    eval_dataset: list of {"input": str, "expected": str or dict}
    
    Run this BEFORE deploying fine-tuned model to decide if it's worth it.
    REGRESSION_THRESHOLD = 0.05: fine-tuned model must be ≥5% better to justify deployment.
    """
    import anthropic
    client = anthropic.Anthropic()
    
    REGRESSION_THRESHOLD = 0.05  # 5% improvement required to justify fine-tuning cost
    
    results = {
        "prompt_engineering": [],
        "rag": [],
    }
    
    if fine_tuned_model_id:
        results["fine_tuned"] = []
    
    for item in eval_dataset:
        expected = item["expected"]
        
        # Approach 1: Prompt engineering (Claude Sonnet)
        pe_response = call_claude_with_prompt(
            client,
            model="claude-sonnet-4-6",
            system=LUMIERE_SYSTEM_PROMPT,
            user=item["input"],
        )
        results["prompt_engineering"].append({
            "score": score_response(pe_response, expected),
            "latency_ms": pe_response.get("latency_ms", 0),
            "cost": estimate_call_cost(pe_response, "claude-sonnet-4-6"),
            "parse_success": pe_response.get("parse_success", True),
        })
        
        # Approach 2: RAG
        context = retrieve_rag_context(item["input"])
        rag_response = call_claude_with_rag(
            client,
            model="claude-sonnet-4-6",
            system=LUMIERE_SYSTEM_PROMPT,
            user=item["input"],
            context=context,
        )
        results["rag"].append({
            "score": score_response(rag_response, expected),
            "latency_ms": rag_response.get("latency_ms", 0),
            "cost": estimate_call_cost(rag_response, "claude-sonnet-4-6"),
            "parse_success": rag_response.get("parse_success", True),
        })
        
        # Approach 3: Fine-tuned model (if available)
        if fine_tuned_model_id:
            ft_response = call_fine_tuned_model(
                fine_tuned_model_id,
                item["input"],
            )
            results["fine_tuned"].append({
                "score": score_response(ft_response, expected),
                "latency_ms": ft_response.get("latency_ms", 0),
                "cost": estimate_call_cost(ft_response, fine_tuned_model_id),
                "parse_success": ft_response.get("parse_success", True),
            })
    
    # Summarize results
    summary = {}
    for approach, scores in results.items():
        all_scores = [s["score"] for s in scores]
        summary[approach] = ModelEvalResults(
            model_id=fine_tuned_model_id if approach == "fine_tuned" else "claude-sonnet-4-6",
            approach=approach,
            avg_score=mean(all_scores),
            std_dev=stdev(all_scores) if len(all_scores) > 1 else 0,
            min_score=min(all_scores),
            parse_rate=sum(s["parse_success"] for s in scores) / len(scores),
            avg_latency_ms=mean(s["latency_ms"] for s in scores),
            avg_cost_per_call=mean(s["cost"] for s in scores),
        )
    
    # Print comparison table
    print(f"\n{'Approach':<25} {'Avg Score':>10} {'Std Dev':>9} {'Parse%':>8} {'Latency':>10} {'Cost/call':>12}")
    print("-" * 80)
    for approach, result in summary.items():
        print(
            f"{approach:<25} "
            f"{result.avg_score:>10.3f} "
            f"{result.std_dev:>9.3f} "
            f"{result.parse_rate*100:>7.1f}% "
            f"{result.avg_latency_ms:>8.0f}ms "
            f"${result.avg_cost_per_call:>10.6f}"
        )
    
    # Decision recommendation
    if fine_tuned_model_id and "fine_tuned" in summary:
        best_baseline = max(summary["prompt_engineering"].avg_score, summary["rag"].avg_score)
        ft_score = summary["fine_tuned"].avg_score
        improvement = ft_score - best_baseline
        
        if improvement >= REGRESSION_THRESHOLD:
            print(f"\n✅ RECOMMENDATION: Deploy fine-tuned model (+{improvement:.2%} improvement)")
        else:
            print(f"\n⚠️  RECOMMENDATION: Keep RAG+prompting (fine-tune only {improvement:.2%} better, threshold is {REGRESSION_THRESHOLD:.0%})")
    
    return summary
```

---

## 10. Deployment and A/B Testing

### Gradual Rollout

```python
import random

class ModelRouter:
    """
    Route requests between baseline and fine-tuned model for A/B testing.
    
    Start with 5% traffic to fine-tuned model.
    If quality holds, increase to 20%, 50%, 100%.
    Roll back immediately if quality degrades.
    """
    
    def __init__(
        self,
        baseline_model: str = "claude-sonnet-4-6",
        fine_tuned_model: str = None,
        fine_tuned_traffic_pct: float = 0.05,  # 5% initially
    ):
        self.baseline_model = baseline_model
        self.fine_tuned_model = fine_tuned_model
        self.fine_tuned_traffic_pct = fine_tuned_traffic_pct
        self.quality_scores = {"baseline": [], "fine_tuned": []}
    
    def route(self, request_id: str = None) -> tuple[str, str]:
        """
        Returns (model_id, variant) where variant is "baseline" or "fine_tuned"
        
        Uses deterministic routing (hash of request_id) for consistency:
        same user always gets same variant in a session.
        """
        if not self.fine_tuned_model:
            return self.baseline_model, "baseline"
        
        # Deterministic: hash request_id to decide variant
        if request_id:
            hash_value = int(hashlib.md5(request_id.encode()).hexdigest(), 16) % 100
            use_fine_tuned = hash_value < (self.fine_tuned_traffic_pct * 100)
        else:
            use_fine_tuned = random.random() < self.fine_tuned_traffic_pct
        
        if use_fine_tuned:
            return self.fine_tuned_model, "fine_tuned"
        return self.baseline_model, "baseline"
    
    def record_quality(self, variant: str, score: float):
        """Record quality score for statistical analysis."""
        self.quality_scores[variant].append(score)
    
    def should_rollback(self, min_samples: int = 100, regression_threshold: float = 0.05) -> bool:
        """
        Check if fine-tuned model is underperforming.
        Returns True if rollback is recommended.
        """
        ft_scores = self.quality_scores["fine_tuned"]
        baseline_scores = self.quality_scores["baseline"]
        
        if len(ft_scores) < min_samples or len(baseline_scores) < min_samples:
            return False  # Not enough data yet
        
        ft_avg = mean(ft_scores[-min_samples:])
        baseline_avg = mean(baseline_scores[-min_samples:])
        
        if ft_avg < baseline_avg - regression_threshold:
            print(f"⚠️  ROLLBACK RECOMMENDED: fine-tuned {ft_avg:.3f} vs baseline {baseline_avg:.3f}")
            return True
        
        return False
```

---

## 11. Hybrid Architecture: Claude + Fine-tuned Model

### When to Use Which Model

```python
from enum import Enum

class TaskType(str, Enum):
    WINE_PAIRING = "wine_pairing"
    MENU_EXTRACTION = "menu_extraction"      # Fine-tuned for format
    ALLERGEN_QUERY = "allergen_query"        # Claude — safety critical
    RESERVATION = "reservation"              # Claude — reasoning
    COMPLAINT = "complaint"                  # Claude — empathy
    REVIEW_CLASSIFY = "review_classify"      # Fine-tuned for speed
    GENERAL_CHAT = "general_chat"            # Claude — flexibility

# Model routing configuration for Lumière
LUMIERE_MODEL_ROUTING = {
    TaskType.WINE_PAIRING:      ("ft:gpt-4o-mini-lumiere-wine-v2", "azure_openai"),
    TaskType.MENU_EXTRACTION:   ("ft:gpt-4o-mini-lumiere-menu-v1", "azure_openai"),
    TaskType.ALLERGEN_QUERY:    ("claude-sonnet-4-6", "anthropic"),  # Safety → Claude
    TaskType.RESERVATION:       ("claude-sonnet-4-6", "anthropic"),  # Reasoning → Claude
    TaskType.COMPLAINT:         ("claude-sonnet-4-6", "anthropic"),  # Empathy → Claude
    TaskType.REVIEW_CLASSIFY:   ("ft:gpt-4o-mini-lumiere-classify-v1", "azure_openai"),
    TaskType.GENERAL_CHAT:      ("claude-haiku-4-5-20251001", "anthropic"),  # General → Haiku
}


def detect_task_type(user_message: str) -> TaskType:
    """Route user message to appropriate model based on task type."""
    message_lower = user_message.lower()
    
    if any(kw in message_lower for kw in ["allerg", "intoleran", "celiac", "nut", "gluten", "dairy free"]):
        return TaskType.ALLERGEN_QUERY  # Always safety → Claude
    
    if any(kw in message_lower for kw in ["wine", "bottle", "pairing", "recommend a wine", "sommelier"]):
        return TaskType.WINE_PAIRING
    
    if any(kw in message_lower for kw in ["book", "reserv", "table", "availability"]):
        return TaskType.RESERVATION
    
    if any(kw in message_lower for kw in ["disappoint", "complaint", "wrong order", "terrible", "unacceptable"]):
        return TaskType.COMPLAINT  # Always empathy → Claude
    
    return TaskType.GENERAL_CHAT
```

---

## 12. Restaurant-Specific Guidance

### For Lumière: Current State

**Prompt engineering + RAG is sufficient for all current use cases.** As of 2026, the evaluation scores are:

| Task | Prompt+RAG Score | Target | Status |
|------|-----------------|--------|--------|
| Wine pairing descriptions | 0.87 | ≥0.80 | ✅ Sufficient |
| Menu item extraction | 0.93 | ≥0.95 | 🟡 Near target |
| Allergen queries | 0.96 | ≥0.95 | ✅ Excellent |
| Reservation assistance | 0.91 | ≥0.85 | ✅ Sufficient |
| Review classification | 0.89 | ≥0.90 | 🟡 Close |

**Decision**: Do not fine-tune yet. Close the gap on menu extraction and review classification with better prompts before considering fine-tuning.

**Trigger for fine-tuning re-evaluation**: If evaluation scores drop below 0.80 after a major model update, or if volume exceeds 500K requests/month and cost analysis shows fine-tuning would save >$500/month.

**Recommended fine-tuning candidates (if needed)**:
1. Wine pairing descriptions — highest volume, most stylistic, 2000+ historical examples available
2. Menu descriptions — clear format, 800+ historical examples, currently 0.93 vs 0.95 target

---

## 13. Junior Developer Walkthrough

**Goal**: Understand why you probably don't need fine-tuning yet.

### The Decision Check

```python
# Step 1: Measure your current prompt quality
from lumiere.eval import run_evaluation

# Run your eval dataset through current system
results = run_evaluation(
    system_prompt=LUMIERE_SYSTEM_PROMPT,
    eval_dataset=WINE_PAIRING_EVAL_SET,  # 50+ labeled examples
    model="claude-sonnet-4-6",
)

print(f"Current score: {results['avg_score']:.2f}")
print(f"Parse rate: {results['parse_rate']:.1%}")

# If avg_score >= 0.80: You don't need fine-tuning ✅
# If avg_score < 0.80:  First try improving the prompt

# Step 2: If quality < 0.80, improve the prompt first
# - Add 5-10 few-shot examples
# - Make the format requirements more explicit
# - Add chain-of-thought instruction
# Re-run evaluation after each change

# Step 3: If prompt engineering can't close the gap, add RAG
# - Use Azure AI Search hybrid search
# - Retrieve top-3 relevant documents
# Re-run evaluation

# Step 4: If RAG + prompts still < 0.80, THEN consider fine-tuning
# By this point you should have 50+ labeled examples from your eval set
# and a clear picture of what's failing
```

---

## 14. Senior Developer Patterns

### Pattern: Automated Quality Gates in CI/CD

```python
# .github/workflows/model_quality_gate.yml equivalent in Python
def run_model_quality_gate(
    system_prompt_file: str,
    eval_dataset_file: str,
    min_quality_score: float = 0.80,
    min_parse_rate: float = 0.98,
) -> bool:
    """
    Run in CI/CD before deploying prompt changes.
    Returns True if quality gate passes, False if it fails.
    
    Prevents deploying prompt changes that degrade quality.
    """
    system_prompt = open(system_prompt_file).read()
    eval_dataset = json.loads(open(eval_dataset_file).read())
    
    results = run_evaluation(system_prompt, eval_dataset, model="claude-sonnet-4-6")
    
    quality_ok = results["avg_score"] >= min_quality_score
    parse_ok = results["parse_rate"] >= min_parse_rate
    
    print(f"Quality gate: {'✅ PASS' if quality_ok else '❌ FAIL'} "
          f"({results['avg_score']:.2f} vs threshold {min_quality_score})")
    print(f"Parse rate: {'✅ PASS' if parse_ok else '❌ FAIL'} "
          f"({results['parse_rate']:.1%} vs threshold {min_parse_rate:.1%})")
    
    return quality_ok and parse_ok

# Use in CI:
# if not run_model_quality_gate("system-prompts/lumiere.txt", "evals/wine_pairing.json"):
#     sys.exit(1)  # Block deployment
```

---

## 15. Tips, Tricks, and Gotchas

### ✅ Do's

**Always measure before deciding**. Quality intuitions are often wrong. Build an eval set of 50+ labeled examples and measure every approach before concluding anything is insufficient.

**Curate training data from production**. The best training data is real conversations that received high quality scores. Use LLM-as-judge (Haiku) to pre-filter, then human review the top candidates.

**Use validation split**. Always hold out 10-20% of examples for validation. Without a validation set, you can't detect overfitting.

**Pin the fine-tuned model version**. When a new base model version is released, your fine-tuned model may break. Always use the full model string and have a re-training plan.

### ❌ Don'ts

**Don't fine-tune to fix a knowledge problem**. Knowledge changes (prices, menus, regulations) — use RAG, not fine-tuning.

**Don't fine-tune with fewer than 50 examples**. Results are unpredictable and often worse than zero-shot.

**Don't fine-tune without an eval set**. You need to measure before and after to know if it helped.

**Don't skip A/B testing**. Fine-tuning can subtly degrade performance on edge cases even when improving the average. Test with real traffic before full rollout.

**Don't fine-tune Claude** — it's not supported via the Anthropic API as of 2026. Use Azure OpenAI or open models for fine-tuning, and Claude for everything else.

### 🔧 Gotchas

**n_epochs too high causes overfitting**: If your training loss keeps decreasing but validation loss starts increasing, reduce n_epochs. Start with 3.

**The fine-tuned model forgets general capability**: A heavily fine-tuned model may get better at your specific task but worse at general instructions. Always keep a fallback to the base model.

**Data contamination**: If your eval set and training set overlap, your eval scores are inflated. Always split before any training.

**Azure OpenAI fine-tuning deployment**: After fine-tuning, you still need to deploy the model to an Azure endpoint. The model ID alone doesn't give you an inference endpoint.

---

## 16. Quick Reference Cheatsheet

```python
# ── DECISION GATE ─────────────────────────────────────────────────────────────
# Fine-tune ONLY IF ALL of these:
# 1. Prompt engineering quality < 0.80 (measured)
# 2. RAG quality < 0.80 (measured)
# 3. Failure mode is style/format, NOT knowledge
# 4. You have >= 50 labeled training examples
# 5. You have a labeled eval set (never in training)
# 6. Budget approved

# ── DATASET PREP ──────────────────────────────────────────────────────────────
prepare_fine_tuning_dataset(examples, "train.jsonl")
validate_fine_tuning_dataset("train.jsonl")
# Format: {"messages": [{"role": "system"}, {"role": "user"}, {"role": "assistant"}]}

# ── SUBMIT JOB ────────────────────────────────────────────────────────────────
job_id = submit_fine_tuning_job(
    training_file="train.jsonl",
    validation_file="val.jsonl",
    model="gpt-4o-mini-2024-07-18",  # Cost-effective
    n_epochs=3,                       # Start here
    suffix="lumiere-v1",
)

# ── POLL FOR COMPLETION ───────────────────────────────────────────────────────
result = poll_fine_tuning_job(job_id)
fine_tuned_model_id = result["fine_tuned_model"]

# ── EVALUATE ──────────────────────────────────────────────────────────────────
comparison = compare_approaches(eval_dataset, fine_tuned_model_id=fine_tuned_model_id)
# REGRESSION_THRESHOLD = 0.05 (5% improvement required to justify deployment)

# ── DEPLOY WITH A/B TEST ──────────────────────────────────────────────────────
router = ModelRouter(
    baseline_model="claude-sonnet-4-6",
    fine_tuned_model=fine_tuned_model_id,
    fine_tuned_traffic_pct=0.05,  # Start with 5%
)

# ── ROLLBACK TRIGGER ──────────────────────────────────────────────────────────
if router.should_rollback(min_samples=100):
    router.fine_tuned_traffic_pct = 0.0  # Kill fine-tuned traffic

# ── COST ESTIMATE ─────────────────────────────────────────────────────────────
# 500 examples × 400 tokens × 3 epochs × $0.003/1K = ~$1.80 training cost
# gpt-4o-mini fine-tuned inference: ~$0.0003/1K input, $0.0012/1K output
```
