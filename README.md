# Photography Teaching System

A personalised one-on-one photography teaching system powered by large language models and vision AI. The system learns who the student is, what they want to express, and adapts every lesson to their intent and skill level.

## How it works

The system has two phases that run sequentially in a single app.

**Phase 1 — Interview**
A conversational agent gets to know the student through natural dialogue — their photographic intent, the subjects they are drawn to, their device, and their visual references. No skill questionnaires. The profile is built from what they say and how they say it.

**Phase 2 — Teaching**
A teacher agent runs personalised lesson sessions. Each session follows a structured loop:

```
Explain concept → Assign task → Student submits photo
→ Evaluate → Gap analysis → Feedback → Reflect → repeat
```

Feedback always connects to the student's intent, addresses one issue at a time, and teaches the underlying principle — not just the symptom.

## Architecture

```
app.py                   # unified Gradio web interface
│
├── interview/
│   ├── agent.py         # InterviewAgent — conversation + profile extraction
│   └── profile.py       # UserProfile, SkillModel, SessionRecord
│
└── teaching/
    ├── models.py         # shared data structures
    ├── evaluator.py      # AssignmentEvaluationAssistant — photo analysis
    ├── planner.py        # LessonPlanningAssistant — concept + assignment selection
    └── teacher.py        # TeacherAgent — orchestrator, feedback, session memory
```

The teacher uses two specialist assistants internally:
- **Evaluator** — analyses submitted photos across 5 dimensions (light, composition, colour, subject clarity, moment/storytelling). Returns observations only — no scores, no teaching language.
- **Planner** — recommends the next concept and assignment based on the student's profile and skill history. Called only at session start or when the student is ready to advance.

## Supported backends

| Component | Options |
|---|---|
| Teacher + Planner (text) | OpenAI `gpt-4o-mini` · Google `gemini-2.5-flash` |
| Evaluator (vision) | OpenAI `gpt-4o` · Qwen2.5-VL-3B (local) |

## Setup

**1. Clone and create environment**
```bash
git clone git@github.com:ShadowsKuming/photography-teaching-system.git
cd photography-teaching-system
conda env create -f environment.yml
conda activate photography-teaching
```

**2. Install PyTorch** (only needed for local Qwen evaluator)

Choose the right variant for your hardware at https://pytorch.org/get-started/locally/

**3. Add API keys**

Create a `.env` file in the project root:
```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...        # optional, only if using Gemini
```

**4. Run**
```bash
python app.py
```
Then open `http://localhost:7860` in your browser.

## Demo

https://github.com/user-attachments/assets/dialogue_example.mp4
