# Project 1: Guardrail & Evaluation Layer for Agentic Systems

## 1. Problem Statement

Every team that ships a LangGraph/CrewAI/Claude Agent SDK agent into production eventually hits the same wall: **how do you know the agent is actually working correctly?** Unlike traditional software, agent outputs are non-deterministic — the same input can produce different reasoning paths, tool calls, and final answers across runs. Most student and hobbyist projects stop at "the agent works in my demo." Production teams cannot ship on that basis.

This project builds the **missing layer**: a standalone evaluation and guardrail harness that can be pointed at *any* LangGraph/CrewAI agent and answer:
- Did it complete the task? (task-success rate)
- Did it hallucinate or fabricate information? (groundedness score)
- Did it violate a safety/policy rule? (guardrail violations)
- How consistent is it across repeated runs? (variance/reliability)
- Where exactly did it go wrong? (trace-level root-cause)

## 2. Why This Matters — Market & Future Scope

| Signal | Detail |
|---|---|
| Funding activity | AI evaluation/observability startups (e.g. Braintrust-class tooling) have raised large rounds in 2025–26, confirming this is a distinct, fundable category — not a feature bolted onto agent frameworks |
| Hiring language | Job descriptions increasingly separate "agent builder" from "AI reliability/eval engineer" — the latter is newer and less contested |
| Ecosystem maturity | LangSmith, native tracing in LangGraph, and MCP's growth (1,800+ servers by March 2026) mean the *plumbing* for tracing exists — what's missing is the *judgment layer* on top, which is exactly what this project builds |
| Future extensions | Automated regression testing for agents (like CI/CD but for prompts/agents), red-teaming automation, cost-vs-accuracy tradeoff dashboards, multi-agent conflict detection |

This is a layer that scales *horizontally* — once built, it can evaluate any agent you or others build afterward (including your own Code-Review Agent or OrgMind), which makes it a strong capstone that ties your whole portfolio together.

## 3. Architecture

```
┌─────────────────────┐        ┌──────────────────────────┐
│   Agent Under Test    │──────▶│   Trace Capture Layer     │
│ (LangGraph / CrewAI /  │        │ (LangSmith or custom       │
│  Claude Agent SDK)    │        │  middleware logging every   │
│                        │        │  node, tool call, and I/O)  │
└─────────────────────┘        └────────────┬─────────────┘
                                             │
                                             ▼
                                ┌──────────────────────────┐
                                │      Evaluation Engine     │
                                │  ┌───────────────────────┐ │
                                │  │ Groundedness Scorer    │ │ (LLM-as-judge + retrieval overlap)
                                │  ├───────────────────────┤ │
                                │  │ Task-Completion Scorer │ │ (rule-based + LLM-as-judge)
                                │  ├───────────────────────┤ │
                                │  │ Guardrail Rule Checker │ │ (regex + classifier + policy LLM)
                                │  ├───────────────────────┤ │
                                │  │ Consistency Checker    │ │ (multi-run variance)
                                │  └───────────────────────┘ │
                                └────────────┬─────────────┘
                                             │
                                             ▼
                                ┌──────────────────────────┐
                                │   Results Store (Postgres) │
                                └────────────┬─────────────┘
                                             │
                                             ▼
                                ┌──────────────────────────┐
                                │   Dashboard (Streamlit/    │
                                │   FastAPI + React)         │
                                │   - per-run drill-down     │
                                │   - trend charts over time │
                                │   - flagged failure cases  │
                                └──────────────────────────┘
```

## 4. Core Components & Tech Stack

| Component | Purpose | Suggested Tools |
|---|---|---|
| Trace capture | Record every agent step (node, tool call, input/output) | LangSmith SDK, or custom middleware if you want full control |
| Groundedness scorer | Check if claims in the output are supported by retrieved context | LLM-as-judge (Groq/LLaMA) + embedding similarity overlap |
| Task-completion scorer | Binary/graded pass-fail against a labeled test set | Rule-based checks + LLM-as-judge fallback |
| Guardrail rule checker | Flag policy violations (PII leakage, unsafe instructions, off-topic drift) | Regex/keyword layer + lightweight classifier |
| Consistency checker | Run the same input N times, measure output variance | Custom scripts, embedding-distance clustering |
| Storage | Persist run history for trend analysis | PostgreSQL |
| Dashboard | Visualize scores, drill into failing traces | Streamlit (fast) or FastAPI + React (more polished) |

## 5. Build Roadmap

| Phase | Deliverable |
|---|---|
| 1 | Pick 1–2 target agents to evaluate (can start with a toy agent, then plug in your own Code-Review Agent later) |
| 2 | Build trace capture — get full visibility into every agent step |
| 3 | Build the groundedness + task-completion scorers with a hand-labeled eval set (30–50 examples is enough to start) |
| 4 | Add guardrail rule checks |
| 5 | Add multi-run consistency checking |
| 6 | Build the dashboard and deploy (Docker + cloud host) |
| 7 (stretch) | Add automated regression testing — re-run the eval suite whenever the agent's prompt/config changes, like CI for agents |

## 6. Why This Differentiates You

- Almost no final-year projects in your peer group will have built an **evaluation tool** rather than an agent — this is a meta-layer that shows systems-level thinking.
- It's directly reusable: you can point it at your own Code-Review Agent (Project 2) as a live case study, giving you a portfolio where projects reinforce each other instead of sitting in isolation.
- It maps to a hiring category ("AI reliability/eval engineer") that is newer and less saturated than "agent builder."
