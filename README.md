# FN² — Fractal Negative Feedback Node Agent Framework

We believe the next meaningful step for autonomous agents is **not** bigger models, more tools, or fancier prompts.  
It is **better control architectures** — systems that can systematically critique their own outputs, decompose problems recursively, manage uncertainty explicitly, and escalate gracefully when they hit fundamental limits.

FN² is a minimalist, early-stage attempt to build exactly that:  
a **negative feedback cognitive loop** with **fractal recursion**, designed from the ground up for long-term iteration, deep extensibility, and eventual multi-agent coordination.

## Core Architectural Invariants

These are the non-negotiable principles that define FN²:

- Negative feedback is first-class, not optional  
  Every cycle includes explicit synthesis + verification. No blind chain-of-thought optimism.

- Fractal recursion over flat decomposition  
  Tasks can decompose into subtasks of the same shape, with bounded depth but unbounded nesting in theory.

- Explicit uncertainty & verification step  
  Outputs carry uncertainty scores; verification is not implicit confidence — it's a separate, structured decision.

- Escalation paths as first-class citizens  
  When the loop cannot resolve internally (high uncertainty, max retries, capability limit), it escalates — to human, to another agent, or to explicit failure — instead of hallucinating.

- Traceability & debuggability over black-box magic  
  Full event tracing, task tree visualization, dry-run mode for replaying state transitions without real LLM calls.

- Minimal magic, maximal extensibility  
  No hidden prompt tricks, no massive dependency tree. Core is < 3000 LOC. Everything is pluggable.

## Our Long-term Design Philosophy

These convictions shape every major design decision:

1. **The future of inference is on-device**  
   Most reasoning will eventually run on edge devices. Supporting capable small models is a first-class priority. Small-model limitations constrain complex problem-solving, not everyday assistant usability. Current on-device models are already sufficient for reliable, OpenCLAW-style agents.

2. **Trustworthy lower bounds matter more than ever-expanding upper bounds**  
   As LLMs grow more powerful, they extend the ceiling. But in the vast majority of real-world use cases, users need a dependable floor — consistent, predictable, verifiable behavior. Structured feedback control loops are the only reliable path to that.

3. **Cost, sovereignty, safety, and regulatory realities cannot be ignored**  
   Inference costs are dropping fast, yet for large-scale, always-on deployment, cost remains critical. Data sovereignty, security, and geopolitical constraints make local/edge deployment non-negotiable. True agentic scale only becomes possible after on-device intelligence reaches maturity. **Ultimately, LLMs are trained on the collective knowledge of all humanity — they should be directly accessible to every person, no matter where they are or who they are.**

4. **Human organizations are the enduring substrate — agents must evolve to fit them**  
   Human structures (teams, hierarchies, accountability flows) will not vanish because of LLMs; instead, LLMs and agents will co-evolve to serve and strengthen those structures (while those structures simplify and optimize in response). This is Conway's Law applied to socio-technical systems. Agent architectures must therefore be **human-centered by design**: escalation is first-class, permission boundaries are respected, auditability is built-in, and integration with human decision loops is foundational — not an afterthought.

## Current Status (March 2026)

- Core state machine + event bus (Board) is stable  
- Negative feedback loop (Analyzer → Executor → Synthesizer → Controller) is implemented  
- Dry-run / mock mode works well for testing control flow  
- Real LLM mode (Analyzer + Synthesizer) is running but brittle — prompt engineering & tool integration still very early  
- Tool/skill calling chain is skeleton-only (real tools coming soon)

## Honest Limitations

- Real LLM runs are unstable (frequent over-clarification, shallow decomposition, poor subtask synthesis)  
- No long-term memory / cross-task learning yet  
- Tool ecosystem is minimal (search, code exec, file ops are next priorities)  
- No production-grade safety, rate-limiting, or persistence  
- Not benchmark-competitive right now — focus is architecture, not leaderboard

## What FN² is NOT trying to be (right now)

- Another ReAct / AutoGPT / LangGraph clone  
- A prompt-engineering showcase  
- A production-ready framework  
- A system that wins agent benchmarks out of the box

We are trying to build the **control skeleton** that others can later build strong agents on top of.

## Who We Want to Work With

If any of these resonate deeply with you, we would love to build this direction together:

- Frustrated with brittle prompt-chaining agents  
- Believe negative feedback, reflection, and explicit verification are the path to reliability  
- Genuinely interested in recursive decomposition + intelligent subtask aggregation  
- Willing to invest time in prompt tuning, tool design, memory patterns — not just quick demos  
- Thinking long-term about multi-agent coordination, escalation, capability boundaries  
- Not afraid to refactor from the ground up, write tests, document architecture

## How to Get Involved

**Quick wins**  
- Improve Analyzer / Matcher / Synthesizer prompts (currently the biggest bottleneck)  
- Implement first real tools (web search, python exec, file read/write highest priority)  
- Add unit tests for Board state transitions  
- Help visualize task trees (CLI or simple web UI)

**Deeper contributions**  
- Better subtask result aggregation & synthesis  
- Uncertainty-aware retry/escalate strategies  
- Long-term memory patterns (vector? key-value? episodic?)  
- Multi-agent coordination primitives  
- Reflection / critique loop separation

Open an issue with "Proposal:" prefix for architectural ideas.

## License

MIT

---

**Last updated: March 2026**

We are not chasing short-term hype.  
We want to walk this path — negative feedback + fractal recursion — further, together with people who see the same long game.

If this feels like the right direction to you, welcome to contribute via issue / PR / DM (@bfzhao on X).

Let's build.