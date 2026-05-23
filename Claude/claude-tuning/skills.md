# skills.md — Claude Skills: Creation, Optimization, and Triggering

> **Purpose**: How to design, write, test, and optimise Claude skills for Cowork and Claude Code.  
> **Applies to**: Claude Cowork (desktop), Claude Code CLI, Anthropic Plugin system.  
> **Owner**: jose@hybridgenai.com

---

## 1. What Is a Skill?

A **skill** is a self-contained instruction bundle that extends Claude's behaviour for a specific task domain. Skills live in SKILL.md files and are loaded into Claude's context when triggered, giving Claude:
- Precise tool usage instructions
- Domain-specific best practices
- Output format specifications
- Example inputs and outputs

Skills are to Claude what plug-ins are to other software — modular, composable, and replaceable without changing the base model.

---

## 2. Skill File Structure (SKILL.md)

```markdown
---
name: skill-name
description: "Trigger description — written to match user intent phrases"
license: MIT | Proprietary
---

# Skill Title

## Overview
One paragraph explaining what this skill does and when to use it.

## Prerequisites
- Required tools or MCP servers
- Required permissions
- Environment variables

## Step-by-Step Instructions
### Step 1: [Action Name]
Detailed instructions for this step, including:
- Exact tool calls to make
- How to handle errors
- What to validate before proceeding

### Step 2: [Next Action]
...

## Output Format
Exact specification of what the final output looks like.

## Examples
### Example 1: [Scenario Name]
Input: ...
Expected output: ...

## Error Handling
| Error | Cause | Resolution |
|-------|-------|------------|
```

---

## 3. Writing High-Performance Skill Descriptions

The `description` field in the SKILL.md front matter is what Claude uses to decide whether to invoke the skill. This is the most important text in the file.

### Principles for Effective Descriptions

**Cover the trigger vocabulary**: Include every phrase a user might say that should invoke the skill.

```yaml
# ❌ Narrow — misses many trigger phrases
description: "Use when creating Excel files"

# ✅ Comprehensive
description: "Use when the user wants to create, edit, read, analyse, or convert  
spreadsheet files including .xlsx, .xls, .csv, tabular data, Excel workbooks,  
financial models, budgets, pivot tables, charts in spreadsheet format, or  
any request where the output should be a spreadsheet file."
```

**Specify exclusions** to prevent false triggers:
```yaml
description: "... Do NOT use for Word documents, HTML tables, or database queries."
```

**Use the same language the user uses**: Users say "make a deck" not "create a PPTX file". Include both.

---

## 4. Skill Composition Patterns

### 4.1 Sequential Skill Chain
One skill's output becomes the next skill's input.

```
User: "Extract the invoice data and add it to the budget spreadsheet"
  → Document Intelligence skill (extract fields)
  → xlsx skill (append row to spreadsheet)
```

### 4.2 Skill with Sub-Tool Delegation
The skill orchestrates multiple tool calls internally.

```markdown
## Step 2: Process Each Document
For each PDF file found:
  1. Call Read tool to get file contents
  2. Call Bash tool to run: python scripts/extract.py <file>
  3. Validate the JSON output has all required fields
  4. If validation fails, retry once with corrected parameters
```

### 4.3 Conditional Skill Branches
Skills can include conditional logic for different input types.

```markdown
## Step 1: Detect Document Type
Run: python scripts/detect_type.py <file_path>
- If output is "invoice": proceed to Step 2a (Invoice Processing)
- If output is "menu": proceed to Step 2b (Menu Processing)
- If output is "unknown": ask the user to specify the document type
```

---

## 5. Optimising Skill Loading Cost

Skills are loaded into Claude's context on demand. Large skills consume tokens every time they're invoked.

| Optimisation | Technique |
|---|---|
| Keep SKILL.md under 2,000 tokens | Prune examples; reference external docs |
| Split large skills | Separate "create" and "edit" into distinct skills |
| Use lazy loading | Only load step 3+ details when steps 1-2 complete |
| Cache skill output | If the same skill call produces identical output, cache the result |
| Front-load critical instructions | Put the most-used steps first — Claude reads sequentially |

---

## 6. Testing Skills

### Unit Test: Trigger Accuracy
```python
# Test that skill triggers on expected phrases
trigger_phrases = [
    "create an Excel file",
    "make a spreadsheet",
    "build a budget in xlsx",
    "export to Excel",
]
for phrase in trigger_phrases:
    assert skill_router.should_invoke("xlsx", phrase), f"Failed to trigger on: {phrase}"
```

### Integration Test: Full Skill Execution
```python
# Test the skill end-to-end in a sandbox
result = run_skill("xlsx", "Create a wine list spreadsheet with 5 bottles")
assert Path(result.output_file).exists()
assert result.output_file.endswith(".xlsx")
assert validate_xlsx_structure(result.output_file)
```

### Regression Test: Known Edge Cases
Document every edge case that has broken the skill in a test suite. Run before every skill update.

---

## 7. Skill Governance

- Version every skill: `version: "1.2.0"` in front matter
- Change log in the skill file: track what changed and why
- Owner field: who to contact for questions
- Test results: record evaluation scores for each version
- Deprecation: mark old skills `deprecated: true` and point to the replacement

---

## 8. Restaurant AI Example Skills

| Skill | Trigger Phrase | Description |
|---|---|---|
| `wine-pairing` | "pair wine with", "wine recommendation" | Retrieves wine list from AI Search; uses sommelier persona |
| `invoice-extract` | "process invoice", "extract supplier data" | Runs Document Intelligence on PDF; exports to xlsx |
| `menu-update` | "update the menu", "add a dish" | Reads current menu markdown; applies changes; writes back |
| `staff-brief` | "morning brief", "daily summary" | Aggregates reservation data, specials, and alerts |
