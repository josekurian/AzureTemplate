const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, VerticalAlign, PageNumber, PageBreak, TableOfContents
} = require('docx');
const fs = require('fs');

const C = {
  primary: "1B2A4A", accent: "2563EB", light: "DBEAFE", alt: "F0F7FF",
  header: "1B2A4A", headerTxt: "FFFFFF", darkText: "111827", subText: "374151",
  green: "166534", greenBg: "DCFCE7", orange: "9A3412", orangeBg: "FEF3C7",
  purple: "5B21B6", purpleBg: "EDE9FE", red: "991B1B", redBg: "FEE2E2",
};
const F = "Calibri";
const bdr = { style: BorderStyle.SINGLE, size: 1, color: "D1D5DB" };
const bdrs = { top: bdr, bottom: bdr, left: bdr, right: bdr };

const h1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: F, size: 34, bold: true, color: C.primary })], spacing: { before: 400, after: 140 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.accent, space: 4 } } });
const h2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: F, size: 26, bold: true, color: C.accent })], spacing: { before: 280, after: 100 } });
const h3 = t => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t, font: F, size: 22, bold: true, color: C.primary })], spacing: { before: 200, after: 80 } });
const body = (t, opts = {}) => new Paragraph({ children: [new TextRun({ text: t, font: F, size: 21, color: C.darkText, ...opts })], spacing: { before: 60, after: 60 } });
const code = t => new Paragraph({ children: [new TextRun({ text: t, font: "Courier New", size: 18, color: "1E3A5F" })], spacing: { before: 20, after: 20 }, indent: { left: 720 } });
const tip = (label, t, col) => new Paragraph({ children: [new TextRun({ text: `${label} `, font: F, size: 20, bold: true, color: col }), new TextRun({ text: t, font: F, size: 20, italics: true, color: col })], spacing: { before: 60, after: 60 }, indent: { left: 360 } });
const bullet = (bold, rest = "") => new Paragraph({ numbering: { reference: "b1", level: 0 }, children: [new TextRun({ text: bold, font: F, size: 21, bold: true, color: C.accent }), new TextRun({ text: rest, font: F, size: 21, color: C.darkText })], spacing: { before: 40, after: 40 } });
const pb = () => new Paragraph({ children: [new PageBreak()] });
const sp = (n = 1) => new Paragraph({ children: [new TextRun("")], spacing: { before: 60 * n, after: 0 } });

const hCell = (t, w) => new TableCell({ borders: bdrs, width: { size: w, type: WidthType.DXA }, shading: { fill: C.header, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: t, font: F, size: 19, bold: true, color: C.headerTxt })] })] });
const dCell = (t, w, fill = "FFFFFF", bold = false) => new TableCell({ borders: bdrs, width: { size: w, type: WidthType.DXA }, shading: { fill, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: t, font: F, size: 19, bold, color: C.darkText })] })] });

const twoCol = (rows, w1 = 3200, w2 = 6160) => new Table({ width: { size: w1 + w2, type: WidthType.DXA }, columnWidths: [w1, w2], rows: rows.map((r, i) => new TableRow({ children: [dCell(r[0], w1, i % 2 === 0 ? C.light : "FFFFFF", true), dCell(r[1], w2, i % 2 === 0 ? C.alt : "FFFFFF")] })) });

const threeCol = (hdr, rows, w1 = 2000, w2 = 2600, w3 = 4760) => new Table({
  width: { size: w1 + w2 + w3, type: WidthType.DXA }, columnWidths: [w1, w2, w3],
  rows: [new TableRow({ children: [hCell(hdr[0], w1), hCell(hdr[1], w2), hCell(hdr[2], w3)] }),
  ...rows.map((r, i) => new TableRow({ children: [dCell(r[0], w1, i % 2 === 0 ? C.light : "FFFFFF", true), dCell(r[1], w2, i % 2 === 0 ? C.alt : "FFFFFF"), dCell(r[2], w3, i % 2 === 0 ? C.alt : "FFFFFF")] }))],
});

const kids = [];

// COVER
kids.push(
  sp(5),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Claude Tuning Guide", font: F, size: 72, bold: true, color: C.primary })], spacing: { before: 0, after: 120 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Performance, Optimization & Production Patterns", font: F, size: 30, italics: true, color: C.accent })], spacing: { before: 0, after: 240 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.accent, space: 4 } }, children: [new TextRun({ text: "20 Tuning Files  •  Complete Reference  •  Code-First  •  Production-Ready", font: F, size: 22, color: C.subText })], spacing: { before: 0, after: 240 } }),
  sp(2),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `Jose Kurian  |  jose@hybridgenai.com  |  HybridGen AI  |  ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}`, font: F, size: 20, italics: true, color: C.subText })] }),
  pb(),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
  pb(),
);

// OVERVIEW
kids.push(
  h1("Overview: The Claude Tuning Library"),
  body("This guide is the master reference for the 20 markdown tuning files in the claude-tuning/ directory. Each file covers a distinct optimisation domain — from writing better prompts and managing tokens, to building production agents and implementing responsible AI controls. Every file is code-first, with working Python, YAML, or JSON examples drawn from real production patterns."),
  sp(),
  body("Reading order: Start with the six Essential files (prompts.md, system-prompts.md, token-optimization.md, memory-management.md, agents.md, safety-guidelines.md). Then progress through High priority files based on your current engineering focus. Reference files can be consulted on-demand."),
  sp(),
  h2("Library Quick-Start Map"),
  twoCol([
    ["Goal", "Files to Read (in order)"],
    ["Reduce API costs", "token-optimization.md → caching.md → model-selection.md → batch-processing.md"],
    ["Improve answer quality", "prompts.md → system-prompts.md → rag-patterns.md → evaluation.md"],
    ["Build reliable agents", "agents.md → tool-use.md → memory-management.md → error-handling.md"],
    ["Production readiness", "error-handling.md → performance-tuning.md → streaming.md → safety-guidelines.md"],
    ["Get structured output", "structured-output.md → tool-use.md → prompts.md"],
    ["Vision / multimodal", "multimodal.md → structured-output.md"],
    ["Async workloads", "batch-processing.md → token-optimization.md"],
    ["Responsible AI", "safety-guidelines.md → evaluation.md → system-prompts.md"],
  ]),
  sp(),
  pb(),
);

// FILE DIRECTORY TABLE
kids.push(
  h1("File Directory: All 20 Tuning Files"),
  body("Each entry below shows the file name, its location in the directory, priority level, primary topic, and a one-line purpose summary."),
  sp(),
);

const files = [
  ["prompts.md", "claude-tuning/prompts.md", "⭐ Essential", "Prompt Engineering", "XML tags, chain-of-thought, negative examples, format control, anti-patterns"],
  ["system-prompts.md", "claude-tuning/system-prompts.md", "⭐ Essential", "System Prompt Design", "5-section structure, versioning, testing framework, domain templates"],
  ["token-optimization.md", "claude-tuning/token-optimization.md", "⭐ Essential", "Token Cost Control", "Prompt compression, caching, output limits, model downgrade, batch API"],
  ["memory-management.md", "claude-tuning/memory-management.md", "⭐ Essential", "Memory Patterns", "Rolling window, progressive summarisation, external KV/vector memory"],
  ["agents.md", "claude-tuning/agents.md", "⭐ Essential", "Agent Orchestration", "ReAct loop, sub-agents, routing, memory patterns, circuit breaker, max steps"],
  ["tool-use.md", "claude-tuning/tool-use.md", "⭐ Essential", "Function Calling", "Tool schema design, tool loop, parallel calls, error contracts, choice modes"],
  ["safety-guidelines.md", "claude-tuning/safety-guidelines.md", "⭐ Essential", "Safety & Responsible AI", "Guardrails, jailbreak patterns, PII handling, content policy, audit logging"],
  ["performance-tuning.md", "claude-tuning/performance-tuning.md", "High", "Latency & Throughput", "TTFT reduction, streaming, async parallelism, response caching, rate limits"],
  ["caching.md", "claude-tuning/caching.md", "High", "Prompt Caching", "Cache control headers, placement rules, TTL, warming, ROI calculator"],
  ["structured-output.md", "claude-tuning/structured-output.md", "High", "Reliable JSON/Data Output", "Prefill technique, Pydantic + tool use, robust JSON parser, retry pattern"],
  ["error-handling.md", "claude-tuning/error-handling.md", "High", "Error & Retry Patterns", "Error taxonomy, backoff, context overflow, fallback tiers, timeout layering"],
  ["rag-patterns.md", "claude-tuning/rag-patterns.md", "High", "RAG Architecture", "Query rewriting, chunking strategies, hybrid search, context formatting, groundedness"],
  ["evaluation.md", "claude-tuning/evaluation.md", "High", "Quality Evaluation", "LLM-as-judge, golden datasets, dimension scoring, CI/CD gate, regression alerts"],
  ["model-selection.md", "claude-tuning/model-selection.md", "High", "Model Choice Framework", "Opus vs Sonnet vs Haiku decision tree, cascade pattern, cost calculator, version pinning"],
  ["streaming.md", "claude-tuning/streaming.md", "Medium", "Streaming Responses", "Sync/async streaming, SSE, tool-use streaming, UI patterns, partial JSON handling"],
  ["context-management.md", "claude-tuning/context-management.md", "Medium", "Context Window Planning", "Budget allocation, token counting API, dynamic injection, map-reduce for large docs"],
  ["multimodal.md", "claude-tuning/multimodal.md", "Medium", "Vision & Images", "Base64/URL inputs, multi-image, OCR, dish photo analysis, cost optimisation"],
  ["cost-optimization.md", "claude-tuning/cost-optimization.md", "Medium", "Cost Governance", "Driver hierarchy, model right-sizing, response caching, budget tracking, alerts"],
  ["batch-processing.md", "claude-tuning/batch-processing.md", "Medium", "Async Batch API", "50% cost reduction, batch creation, polling, result collection, nightly pipeline"],
  ["fine-tuning.md", "claude-tuning/fine-tuning.md", "Reference", "Fine-Tuning Decision", "When to fine-tune vs RAG vs prompts, training data format, evaluation approach"],
];

const fileTable = new Table({
  width: { size: 9360, type: WidthType.DXA }, columnWidths: [1440, 2400, 880, 1440, 3200],
  rows: [
    new TableRow({ children: [hCell("File", 1440), hCell("Location", 2400), hCell("Priority", 880), hCell("Domain", 1440), hCell("Purpose", 3200)] }),
    ...files.map((r, i) => new TableRow({ children: [dCell(r[0], 1440, i%2===0?C.light:"FFFFFF", true), dCell(r[1], 2400, i%2===0?C.alt:"FFFFFF"), dCell(r[2], 880, i%2===0?C.alt:"FFFFFF"), dCell(r[3], 1440, i%2===0?C.alt:"FFFFFF"), dCell(r[4], 3200, i%2===0?C.alt:"FFFFFF")] })),
  ],
});
kids.push(fileTable, sp(), pb());

// DETAILED SECTIONS
const details = [
  {
    title: "1. prompts.md — Prompt Engineering",
    summary: "The foundational skill for getting reliable outputs from Claude. This file covers the six highest-impact prompt engineering techniques with before/after examples, task-specific prompt templates (classification, extraction, summarisation, code generation), anti-patterns that cause inconsistent behaviour, and a prompt versioning system.",
    keyTechniques: [
      ["XML Tag Structure", "Wrap multi-component inputs in <tags> for dramatically improved parsing. Claude's training includes XML-structured data, making tags a reliable separator."],
      ["Chain-of-Thought", "Instruct Claude to reason step-by-step before answering. Reduces errors on multi-step reasoning tasks by 20-40%."],
      ["Positive + Negative Examples", "Show what you want AND what you do not want. Eliminates ambiguity that leads to inconsistent formats."],
      ["Role Assignment", "Assign a specific domain expert role (e.g. 'Michelin-starred sommelier') to activate relevant training patterns."],
      ["Output Format Specification", "Always specify format, length, and structure explicitly. Vague instructions produce variable results that break downstream parsing."],
      ["Positive Constraints", "Frame rules as what Claude should do, not just what it should not do. Negative-only constraints leave Claude guessing the alternative."],
    ],
    examTip: "Best for: any team member writing Claude prompts. Read this file first.",
  },
  {
    title: "2. system-prompts.md — System Prompt Design",
    summary: "System prompts are the most leveraged piece of Claude configuration — they define identity, scope, constraints, output format, and examples for every single request. This file provides a five-section structure that works across any application domain, templates for three common agent types, a versioning system in YAML, and a testing framework.",
    keyTechniques: [
      ["5-Section Structure", "Identity → Scope → Constraints → Output Format → Examples. Sequence matters — Claude weights earlier content more heavily."],
      ["Hard Rule Labelling", "Label non-negotiable constraints with 'HARD RULES' in ALL CAPS for emphasis. Buried critical rules are missed."],
      ["Version Control in YAML", "Store prompts as versioned YAML files with model_optimised_for, eval_score, and change log. Treat prompts like code."],
      ["Prompt Test Suite", "Automated tests that verify the prompt enforces safety rules, scope boundaries, and format compliance on every change."],
    ],
    examTip: "Best for: lead engineers and solution architects designing Claude applications.",
  },
  {
    title: "3. token-optimization.md — Token Cost Control",
    summary: "Token spend is the primary cost driver for Claude API usage. Output tokens cost 3-5× more than input tokens. This file covers the full stack of optimisation techniques from prompt compression (immediate, no-code impact) through model right-sizing, prompt caching, and the Batch API.",
    keyTechniques: [
      ["Prompt Caching", "Mark stable system content with cache_control. Cached tokens cost 10% of normal — 90% discount. Most impactful single optimisation."],
      ["max_tokens Discipline", "Set case-appropriate token limits. Classification = 10 tokens. Paragraph = 300 tokens. Never leave at model maximum."],
      ["Model Cascade", "Try Haiku first (12× cheaper than Sonnet). Escalate to Sonnet only when Haiku confidence falls below 0.85."],
      ["Conversation Trimming", "Implement rolling window history. Unbounded conversation history is the most common cause of runaway token spend in chat apps."],
      ["RAG over Full Context", "Retrieve top-K chunks (500 tokens) instead of injecting full documents (50,000 tokens). 100× reduction in input tokens."],
    ],
    examTip: "Best for: cost-conscious production deployments. Run token monitoring dashboards from day 1.",
  },
  {
    title: "4. memory-management.md — Memory Patterns",
    summary: "Claude has no built-in persistent memory. Every request starts from scratch. This file documents the complete memory architecture: in-context working memory, rolling window conversation history, progressive summarisation, and external persistent stores (KV and vector).",
    keyTechniques: [
      ["Rolling Window", "Keep last N message pairs in context. Simple and predictable token cost. Good for sessions up to 30 minutes."],
      ["Progressive Summarisation", "When history grows long, summarise old turns into a compact memory block. Preserves key facts at low token cost."],
      ["External KV Store", "Persist guest facts (preferences, allergens, past visits) in Azure Table Storage. Load on session start. Unlimited retention."],
      ["Vector Episodic Memory", "Store session summaries as embeddings. Retrieve semantically relevant past episodes on each new session. Enables 'I remember your last visit' capabilities."],
      ["Agent Tool Result Compression", "Compress large tool results before adding to context. Search results: keep top-3. File reads: truncate to 2,000 chars."],
    ],
    examTip: "Best for: any application with multi-turn conversations or return users.",
  },
  {
    title: "5. agents.md — Agent Orchestration",
    summary: "Agents extend Claude from a prompt-response system to an autonomous loop that decides actions, executes tools, and iterates toward a goal. This file covers four agent architecture patterns (single-agent ReAct, orchestrator + subagents, specialist routing, human-in-the-loop), tool design best practices, and four critical reliability patterns.",
    keyTechniques: [
      ["ReAct Loop", "Reason → Act → Observe cycle. Claude selects tool → tool executes → result returned → Claude reasons again. Repeat until goal met or max steps reached."],
      ["Orchestrator + Subagents", "Orchestrator (Opus) handles decomposition; subagents (Sonnet/Haiku) handle execution. Keeps each agent's context focused."],
      ["Max Step Guard", "Hard limit on agent loop iterations prevents infinite loops. 25 steps is a good default for most tasks."],
      ["Circuit Breaker", "After N consecutive tool failures, open the circuit and return a safe degraded response instead of hammering a failing service."],
      ["Human-in-the-Loop", "Require human approval for irreversible or high-stakes actions. Pattern: agent proposes action → human reviews → agent executes."],
    ],
    examTip: "Best for: engineers building autonomous workflows, automation, and agentic features.",
  },
  {
    title: "6. tool-use.md — Function Calling",
    summary: "Tool use (function calling) is Claude's mechanism for taking actions in the world. This file covers the complete tool design lifecycle: schema design, description writing, tool call handling loop, parallel execution, and error contracts.",
    keyTechniques: [
      ["Rich Tool Descriptions", "Tool descriptions are part of your prompt. Include: what it does, when to use it, when NOT to use it, and example parameter values."],
      ["Enum Constraints", "Use enum arrays for parameters with fixed options. Prevents Claude from inventing invalid parameter values."],
      ["Structured Error Returns", "Return {success, error, suggestion} — never throw exceptions. Claude cannot recover from silent failures."],
      ["Parallel Tool Execution", "When Claude calls multiple tools in one turn, execute them concurrently with ThreadPoolExecutor. Reduces latency by N×."],
      ["Tool Choice Forcing", "Use tool_choice={type: 'tool', name: 'X'} to force Claude to call a specific tool. Eliminates tool selection ambiguity."],
    ],
    examTip: "Best for: any engineer adding capabilities to a Claude agent or assistant.",
  },
  {
    title: "7–20: Additional Tuning Files",
    summary: "The remaining 14 files cover production engineering concerns across performance, reliability, cost, and safety.",
    keyTechniques: [
      ["performance-tuning.md", "TTFT decomposition, streaming for perceived performance, async parallelism, response caching patterns"],
      ["caching.md", "Deep dive on prompt caching: placement rules, TTL management, cache warming service, ROI calculator"],
      ["structured-output.md", "Three techniques for reliable JSON: prefill, Pydantic + tool_choice forcing, robust parser with fence stripping"],
      ["error-handling.md", "Error taxonomy (retryable vs non-retryable), exponential backoff, three-tier graceful degradation, timeout layering"],
      ["rag-patterns.md", "Complete RAG pipeline: query rewriting, chunking strategies, hybrid search config, groundedness evaluation"],
      ["evaluation.md", "LLM-as-judge scoring, golden datasets, deployment gate thresholds, regression monitoring"],
      ["model-selection.md", "Decision tree for Opus/Sonnet/Haiku, cascade escalation pattern, cost calculator, version pinning"],
      ["streaming.md", "Sync and async streaming, SSE format for browser, tool-use streaming continuation"],
      ["context-management.md", "200K budget allocation, token counting API, dynamic context injection, map-reduce for large docs"],
      ["multimodal.md", "Image input (base64/URL), multi-image comparison, handwriting OCR, image token cost optimisation"],
      ["cost-optimization.md", "Cost driver hierarchy, budget tracker with daily alerts, response caching, batch API comparison"],
      ["batch-processing.md", "Message Batches API: 50% cost, creation/polling/result patterns, full nightly pipeline example"],
      ["safety-guidelines.md", "Application-layer safety architecture, jailbreak detection regex, PII redaction, content policy config"],
      ["fine-tuning.md", "Build hierarchy (prompt → RAG → fine-tune), decision framework, training data format, evaluation approach"],
    ],
    examTip: "Consult these files as you encounter specific production challenges.",
  },
];

for (const d of details) {
  kids.push(h2(d.title), body(d.summary), sp());
  if (d.keyTechniques.length > 0) {
    kids.push(h3("Key Techniques"), twoCol(d.keyTechniques), sp());
  }
  kids.push(tip("💡 Usage:", d.examTip, C.green), sp(2));
}
kids.push(pb());

// QUICK REFERENCE
kids.push(
  h1("Quick Reference: Optimisation Cheatsheet"),
  h2("Most Impactful Single Changes (Ranked by ROI)"),
  threeCol(
    ["Rank", "Optimisation", "Expected Impact"],
    [
      ["1", "Enable prompt caching on system prompt", "40-90% cost reduction on cached tokens"],
      ["2", "Right-size model (Haiku for routing/classification)", "12× cost reduction for eligible tasks"],
      ["3", "Set max_tokens per task type", "30-60% output token reduction"],
      ["4", "RAG instead of full document context", "Up to 100× input token reduction"],
      ["5", "Batch API for async workloads", "50% flat cost reduction"],
      ["6", "Trim conversation history (rolling window)", "Prevents unbounded cost growth in chat apps"],
      ["7", "Streaming for user-facing responses", "Perceived latency reduced by 5× with no cost change"],
      ["8", "Parallel tool execution", "Latency reduced by N× for N parallel tools"],
      ["9", "Response caching for repeated queries", "Cost reduction proportional to cache hit rate"],
      ["10", "Progressive summarisation for long sessions", "60-80% history token reduction over long sessions"],
    ]
  ),
  sp(2),
  h2("Model Selection at a Glance"),
  twoCol([
    ["Task Type", "Recommended Model"],
    ["Intent routing / query classification", "Claude Haiku 4.5 (claude-haiku-4-5-20251001)"],
    ["Language detection, simple NLP", "Claude Haiku 4.5"],
    ["FAQ answering from static context", "Claude Haiku 4.5"],
    ["RAG Q&A, document summarisation", "Claude Sonnet 4 (claude-sonnet-4-6)"],
    ["Wine pairing, creative generation", "Claude Sonnet 4"],
    ["Code generation, technical analysis", "Claude Sonnet 4"],
    ["Complex multi-step agents", "Claude Opus 4 (claude-opus-4-6)"],
    ["Strategic analysis, ambiguous reasoning", "Claude Opus 4"],
  ]),
  sp(2),
  pb(),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    border: { top: { style: BorderStyle.SINGLE, size: 8, color: C.accent, space: 4 } },
    children: [new TextRun({ text: "Build Smart  ·  Tune Relentlessly  ·  Ship Confidently", font: F, size: 28, bold: true, color: C.primary })],
    spacing: { before: 240, after: 120 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Claude Tuning Guide  |  Jose Kurian  |  jose@hybridgenai.com  |  HybridGen AI  |  2026", font: F, size: 18, italics: true, color: C.subText })],
  }),
);

// BUILD DOC
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 34, bold: true, font: "Calibri", color: C.primary }, paragraph: { spacing: { before: 400, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, font: "Calibri", color: C.accent }, paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 22, bold: true, font: "Calibri", color: C.primary }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [{ reference: "b1", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1008, right: 1008, bottom: 1008, left: 1008 } } },
    headers: { default: new Header({ children: [new Paragraph({ children: [new TextRun({ text: "Claude Tuning Guide", font: "Calibri", size: 18, bold: true, color: C.accent }), new TextRun({ text: "\t\tPerformance, Optimization & Production Patterns", font: "Calibri", size: 18, color: C.subText })], border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.accent, space: 4 } }, tabStops: [{ type: "right", position: 8640 }] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, border: { top: { style: BorderStyle.SINGLE, size: 4, color: "D1D5DB", space: 4 } }, children: [new TextRun({ text: "Page ", font: "Calibri", size: 18, color: C.subText }), new TextRun({ children: [PageNumber.CURRENT], font: "Calibri", size: 18, color: C.subText }), new TextRun({ text: " | jose@hybridgenai.com | Claude Tuning Guide | 2026", font: "Calibri", size: 18, color: C.subText })], spacing: { before: 80 } })] }) },
    children: kids,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('/sessions/cool-intelligent-bell/mnt/Claude/claude-tuning/Claude Tuning Guide.docx', buf);
  console.log('SUCCESS: Claude Tuning Guide.docx written.');
}).catch(e => { console.error(e); process.exit(1); });
