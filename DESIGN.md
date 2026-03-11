# Fractal Agent

**An event-driven, observable agent architecture designed for reliability and local LLMs.**

Most AI agent frameworks rely on large models and prompt loops.
This project explores a different direction:

> Instead of making the LLM smarter, we **constrain the architecture** to make the system reliable.

The LLM is only one component inside a deterministic control system.

---

# Core Ideas

The architecture is built around three principles.

### 1. Bounded Complexity

Agent reasoning is strictly limited:

```
MAX_DEPTH   = 6
MAX_ACTIONS = 5
```

Interpretation:

* If a task cannot be decomposed within **6 levels**, it is considered unsolvable within current capabilities.
* If a step requires more than **5 actions**, the abstraction is considered insufficient.

This prevents runaway planning loops and enforces **hierarchical abstraction**.

---

### 2. Event-Driven System

The system is organized around a central **Board**.

The Board acts as:

* system state
* event bus
* observability dashboard

All components react to events instead of calling each other directly.

```
Task Created
      ↓
Analyzer
      ↓
Matcher
      ↓
Executor
      ↓
Synthesizer
```

This keeps the system **decoupled, inspectable, and controllable**.

---

### 3. Full Observability

All system state is explicit and visible on the Board.

The Board tracks:

* tasks
* actions
* results
* status transitions
* execution traces

This makes the agent **debuggable and interactive**, rather than a black box.

Humans can inspect or intervene at any stage.

---

# Architecture Overview

```
            Board
       (state + events)
              │
          Controller
              │
   ┌──────────┼──────────┐
   │          │          │
Analyzer    Matcher    Executor
   │                      │
   └──────────┬──────────┘
              │
         Synthesizer
              │
           Verify
```

Key characteristics:

* event-driven orchestration
* deterministic scheduling
* capability-constrained execution
* recursive task decomposition

---

# Fractal Reasoning

Tasks are solved using a recursive structure.

```
Task
 └ Subtask
     └ Subtask
         └ Subtask
```

Each node follows the same loop:

```
analyze → match → execute → synthesize → verify
```

This creates a **fractal reasoning structure** with bounded depth.

---

# Why This Works with Local Models

The architecture is designed to work with **smaller or local LLMs**.

Key reasons:

* limited decision space
* small context windows
* deterministic orchestration
* explicit system state

Instead of relying on model size, the system relies on **architecture constraints**.

---

# Design Philosophy

This project treats the agent as a **system**, not a prompt.

```
System  >  Prompt
State   >  Context
Control >  Autonomy
```

Robust agents come from **good architecture**, not prompt tricks.
