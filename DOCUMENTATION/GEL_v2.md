# Project 1 (v2): Guardrail & Evaluation Layer for Agentic Systems

## 1. Problem Statement

Production agent teams cannot ship on "it worked in my demo." This project builds an evaluation and guardrail harness that inspects an agent's execution trace and reports **evaluation signals with known limitations** — not a single objective score — covering task correctness, factual groundedness, and security/safety behavior.

## 2. Phase 1 Scope (Narrowed)

**Target**: single-agent, tool-using architectures only (this includes your own Code-Review Agent, which serves as the first real test subject).

**Framework strategy**: define one canonical **trace schema** — a JSON structure capturing step sequence, tool calls with arguments, per-step inputs/outputs, retrieved context, and timestamps. Each framework's adapter only has to translate its native run object into this schema.

- Adapter 1 (build first): **LangGraph**
- Adapter 2 (build second, to prove the schema generalizes): CrewAI or Claude Agent SDK

## 3. Architecture

```
┌────────────────────┐        ┌──────────────────────────┐
│  Agent Under Test    │──────▶│  Framework Adapter Layer   │
│ (LangGraph, later a  │        │ (translates native run     │
│  2nd framework)      │        │  object → canonical trace   │
│                       │        │  schema)                    │
└────────────────────┘        └────────────┬─────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │   Canonical Trace Store    │
                               │   (Postgres)                │
                               └────────────┬─────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
        ┌────────────────────┐ ┌────────────────────┐  ┌────────────────────┐
        │  Evaluation Engine   │ │  Security Eval Module │  │  Telemetry Layer     │
        │  (see §4)             │ │  (see §5)              │  │  (see §6)             │
        └────────────┬───────┘ └──────────┬─────────┘  └──────────┬─────────┘
                     └───────────────────┼───────────────────────┘
                                            ▼
                               ┌──────────────────────────┐
                               │   Results Store (Postgres) │
                               └────────────┬─────────────┘
                                            ▼
                               ┌──────────────────────────┐
                               │   Dashboard (Streamlit/    │
                               │   FastAPI + React)         │
                               │  - eval signals w/ evidence │
                               │  - security findings         │
                               │  - telemetry/cost trends      │
                               └──────────────────────────┘
```

## 4. Evaluation Engine

### 4.1 Structured Eval-Signal Schema

Every evaluation produces a structured object, not a bare score:

| Field | Purpose |
|---|---|
| `score` | Numeric/categorical judgment |
| `rubric_breakdown` | Sub-scores per criterion (relevance, completeness, safety) |
| `evidence` | Exact spans/citations used to justify the score |
| `confidence` | Self-reported or derived (e.g. agreement across repeated judge calls) |
| `judge_model` + `prompt_version` | Which model/prompt produced this judgment |
| `eval_method` | rule-based / embedding / LLM-judge / human |
| `timestamp` | When the evaluation ran |
| `known_limitations` | Free-text note on this judge's failure modes |

### 4.2 Claim-Level Groundedness (replaces embedding-similarity)

Embedding similarity conflates "sounds similar" with "is factually supported." Instead:

1. **Claim extraction** — LLM decomposes the answer into atomic factual claims
2. **Evidence retrieval** — for each claim, retrieve the specific supporting span from retrieved context
3. **Entailment check** — per (claim, evidence) pair: entailed / contradicted / not-enough-info
4. **Aggregate** — groundedness score = fraction of claims entailed; unsupported/contradicted claims are listed explicitly, not hidden in one number

### 4.3 Evaluator Types

| Type | Use case |
|---|---|
| Rule-based / exact-match | Deterministic checks (format, required fields) |
| Structured validators | Schema validation on tool arguments and outputs |
| Embedding metrics | Cheap first-pass similarity signal (not the sole groundedness check) |
| LLM-as-judge | Task completion, rubric scoring |
| Human review | Spot-checks and calibration benchmark |

### 4.4 Dataset Versioning

Test cases, expected outputs, metadata (difficulty, task type), and dataset version are stored explicitly — so a score is always reproducible against a known dataset snapshot.

## 5. Security Evaluation Module

Regex/keyword checks are a first layer only. Phase 1 adds a dedicated security-eval suite, framed against the OWASP Top 10 for LLM Applications and informed by NIST's AI Risk Management Framework (continuous testing, documented mitigations).

| Check | Method |
|---|---|
| Prompt injection (direct) | Run a known payload library against the agent, check for compliance |
| Indirect prompt injection | Plant an instruction inside a test document in retrieved context, check if the agent obeys it |
| Unauthorized tool calls / permission evaluation | Define an allow-list per agent role; flag any call outside it |
| Tool argument manipulation | Validate tool call arguments against an expected schema |
| Infinite loops / excessive retries | Step-count and repeat-detection thresholds |
| Excessive token/API usage | Sourced from the telemetry layer (§6) against a defined budget |

*Deferred to future work (noted, not built): data exfiltration detection, cross-user/session leakage, multi-agent coordination checks, full insecure-output-handling coverage.*

## 6. Telemetry Layer

**What it is**: continuous, automatic collection of runtime health signals (latency per step, token/API usage, error rates) — the agent-system equivalent of a car's dashboard, as distinct from evaluation (which is a periodic "inspection report" on output quality).

**Integration**: instrument each agent node with OpenTelemetry spans, capturing latency, token count, and cost per step; log structured spans into the same Postgres store used for eval results. No separate SaaS backend required for project scope.

## 7. Agent-Specific Evaluation Features (Phase 1 additions)

| Feature | What it checks |
|---|---|
| Tool-call correctness | Right tool selected, valid arguments supplied |
| Termination checks | Detects loops, runaway planning, excessive retries |
| Trajectory evaluation *(stretch)* | Judges the action sequence, not just the final answer |
| Recovery evaluation *(stretch)* | Tests agent behavior when a tool fails or returns malformed data |

## 8. Feature Priority

| Priority | Included |
|---|---|
| **Must-have (Phase 1 core)** | Narrow single-agent target + canonical trace schema + LangGraph adapter · structured eval-signal schema · claim-level groundedness pipeline · dataset versioning · rule-based + LLM-judge + embedding evaluators · tool-call correctness · termination checks · security: prompt injection, indirect injection, permission eval, tool-arg validation |
| **Should-have (stretch)** | Telemetry integration (OpenTelemetry) · trajectory evaluation · second framework adapter · slice-based evaluation (by task type/difficulty) · evaluator calibration vs. hand-labeled benchmark · recovery evaluation |
| **Could-have (future work, mention only)** | Pairwise A/B agent comparison · inter-rater agreement across judges · confidence intervals · adversarial test-case auto-generation · human feedback loop · multi-agent coordination checks · data-exfiltration/cross-session monitoring |

## 9. Tech Stack & Cost

| Component | Tool | Cost |
|---|---|---|
| Primary LLM (agent + reasoning) | Groq (LLaMA 3.3 70B / 3.1 8B) | Free tier |
| Judge/entailment LLM pool | Google AI Studio (Gemini Flash) — separate quota pool to avoid contention with agent-run calls | Free tier |
| Overflow | OpenRouter / Cloudflare Workers AI free models | Free tier |
| Embeddings | Local sentence-transformers model or free-tier `text-embedding-004` | Free |
| Database | Supabase or Neon (Postgres) | Free tier |
| Hosting | Railway / Render / Fly.io | Free tier |
| Tracing | LangSmith | Free tier |
| Telemetry | Self-hosted OpenTelemetry spans into Postgres | Free |

**Note**: claim-level groundedness makes several LLM calls per evaluated answer (1 extraction + 1 per claim). Split judge/entailment calls onto a separate provider (Gemini) from agent-run calls (Groq) to avoid quota contention during heavy iteration.

## 10. Build Roadmap

| Phase | Deliverable |
|---|---|
| 1 | Canonical trace schema + LangGraph adapter; wire up Postgres trace store |
| 2 | Structured eval-signal schema + rule-based and embedding evaluators |
| 3 | Claim-level groundedness pipeline (extraction → retrieval → entailment) |
| 4 | Security eval module (prompt injection, indirect injection, permission checks, tool-arg validation) |
| 5 | Telemetry layer (OpenTelemetry spans, cost/latency tracking) |
| 6 | Dashboard: eval signals with evidence, security findings, telemetry trends |
| 7 (stretch) | Second framework adapter, trajectory evaluation, evaluator calibration, slice-based breakdowns |

## 11. Why This Differentiates You

- Presents evaluation as a **signal with documented limitations**, not an objective score — a level of rigor most student (and many production) eval tools skip.
- Claim-level groundedness is a genuine technical contribution, not a wrapper around embedding similarity.
- Security evaluation grounded in OWASP/NIST framing shows awareness of how agentic systems actually fail in production, not just whether they answer correctly.
- Deliberately scoped (single-agent, one framework first) rather than an unbuildable "works for any agent" claim — showing engineering judgment as much as technical skill.
