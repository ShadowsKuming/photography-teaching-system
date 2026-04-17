# Photography Teaching System

A personalised one-on-one photography teaching system powered by large language models and vision AI. The system learns who the student is, what they want to express, and adapts every lesson to their intent and skill level — structured like a Duolingo-style progression with milestone tracking and live camera guidance.

---

## How it works

**Phase 1 — Interview**
A conversational agent gets to know the student through natural dialogue — their photographic intent, subjects, device, and visual style preferences. The student picks a visual style from a grid of 6 options. No questionnaires. A structured `UserProfile` is extracted from the conversation.

**Phase 2 — Teaching**
A teacher agent runs personalised lesson sessions. Each session block follows a deterministic loop:

```
Select target skill → Explain concept → Assign task
→ Student shoots (with live camera guidance)
→ Evaluate photo + process → Gap analysis → Feedback
→ Update skill state → Check milestone → Repeat
```

Feedback always connects to the student's photographic intent, addresses one issue at a time, and teaches the underlying principle. Skill levels advance only after 2 successful sessions out of 3 (not a single lucky shot). Milestones track overall progression: Beginner → Developing → Intermediate → Advanced.

---

## System architecture

The system is split into a Python backend (FastAPI) and a React + Capacitor frontend.

```
photography-teaching-system/
│
├── backend/                          # Python — all logic and API
│   ├── config.py                     # Env config via pydantic-settings, validated at startup
│   │
│   ├── models/                       # Pydantic data contracts (interface boundaries)
│   │   ├── profile.py                # UserProfile, SkillState, SkillDimension, MilestoneState
│   │   ├── session.py                # LiveSessionContext, SessionBlockResult, ObservedIssue
│   │   └── teaching.py               # SkillDefinitions, EvaluationReport, GapAnalysis, LessonPlan
│   │
│   ├── core/                         # Domain logic — each component independently testable
│   │   ├── interview.py              # InterviewAgent — state machine, profile extraction
│   │   ├── progression.py            # Deterministic loop logic (no LLM): skill selection,
│   │   │                             #   advance/retry/stuck rules, milestone computation
│   │   ├── evaluator.py              # Photo analyser — stateless, vision LLM, 5 dimensions
│   │   ├── planner.py                # Lesson planner — stateless, selects concept + assignment
│   │   ├── teacher.py                # Session orchestrator — calls evaluator → progression
│   │   │                             #   → gap analysis → feedback → prose conversion
│   │   ├── llm.py                    # Unified LLM wrapper (OpenAI + Gemini, JSON parsing,
│   │   │                             #   retry logic, fallbacks)
│   │   └── storage.py                # Profile persistence (JSON files in profiles/)
│   │
│   └── api/                          # FastAPI — thin HTTP layer, no business logic
│       ├── app.py                    # FastAPI app, CORS, router mounts
│       ├── schemas.py                # API request/response models (separate from domain models)
│       ├── sessions.py               # In-memory session store (interview + teaching sessions)
│       └── routes/
│           ├── interview.py          # POST /interview/start|chat|style|name|complete
│           ├── teaching.py           # POST /teach/start|submit|next  GET /teach/{id}/profile
│           └── profiles.py           # GET/DELETE /profiles/{name}
│
├── camera-protoype/                  # React + Capacitor frontend (web + iOS + Android)
│   └── src/
│       ├── App.tsx                   # Top-level state machine: landing → interview → teaching
│       ├── types/index.ts            # TypeScript interfaces matching backend schemas
│       ├── api/client.ts             # Typed API client for all 11 endpoints
│       ├── hooks/
│       │   ├── useInterview.ts       # Interview session state + API calls
│       │   └── useTeaching.ts        # Teaching session state + API calls
│       ├── components/
│       │   ├── Camera.tsx            # Live camera: web (getUserMedia) + native (Capacitor)
│       │   │                         #   with rule-of-thirds grid, brightness analysis,
│       │   │                         #   tilt detection, skill-specific live cues
│       │   ├── ChatBubble.tsx        # Chat message component
│       │   ├── StyleGrid.tsx         # 6-option visual style picker
│       │   └── SkillProgress.tsx     # Skill bars + milestone badge
│       └── pages/
│           ├── Landing.tsx           # New student / returning student
│           ├── Interview.tsx         # Chat + style grid → profile extraction
│           └── Teaching.tsx          # Lesson → camera/upload → intent → feedback loop
│
└── profiles/                         # Student profiles (auto-created, gitignored)
```

---

## Key data contracts

All components communicate through typed Pydantic models. These are the interface boundaries — bugs cannot silently cross them.

| Contract | Produced by | Consumed by |
|---|---|---|
| `UserProfile` | `InterviewAgent` | `TeacherAgent`, `Planner`, `Progression` |
| `LiveSessionContext` | Frontend camera layer | `TeacherAgent` |
| `SessionBlockResult` | `TeacherAgent` | Frontend UI (maps to action button) |
| `EvaluationReport` | `Evaluator` | `TeacherAgent` (gap analysis) |
| `LessonPlan` | `Planner` | `TeacherAgent`, Frontend UI |

---

## Skill system

Five core skill dimensions, each scored 1–5:

| Dimension | Applies to | Live detectable |
|---|---|---|
| Composition | All subjects | Yes |
| Lighting | All subjects | Yes (brightness analysis) |
| Subject clarity | All subjects | Yes |
| Pose & expression | Portrait only | Yes |
| Background control | All subjects | Yes |

**Milestone thresholds:**

| Milestone | Condition |
|---|---|
| Beginner | Starting state |
| Developing | Composition + lighting + subject clarity all ≥ 3 |
| Intermediate | All 5 dimensions ≥ 3 AND composition + lighting ≥ 4 |
| Advanced | All 5 dimensions ≥ 4 |

**Advancement rule:** A skill level increments only after 2 advances in the last 3 attempts — not a single success. A stuck protocol triggers after 3 consecutive retries, simplifying the assignment scope.

---

## Where to make changes

The system is designed so each type of refinement maps to exactly one place. This section tells you where to go without having to read everything.

---

### UI & visual design

| What you want to change | Where to go | What to look for |
|---|---|---|
| Page layout or overall flow | `camera-protoype/src/pages/` | `Landing.tsx`, `Interview.tsx`, `Teaching.tsx` |
| Camera viewfinder UI | `camera-protoype/src/components/Camera.tsx` | JSX return block |
| Style grid appearance | `camera-protoype/src/components/StyleGrid.tsx` | `STYLES` array + JSX |
| Skill progress display | `camera-protoype/src/components/SkillProgress.tsx` | `MILESTONE_COLORS`, bar rendering |
| Chat bubble design | `camera-protoype/src/components/ChatBubble.tsx` | Tailwind classes |
| Colours, spacing, typography | Any component file | Tailwind utility classes inline |
| Action button labels (Try again / Next challenge) | `camera-protoype/src/pages/Teaching.tsx` | `ACTION_LABELS` constant |

---

### Interview behaviour

| What you want to change | Where to go | What to look for |
|---|---|---|
| Conversation tone or personality | `backend/core/interview.py` | `_SYSTEM` constant |
| When the style grid appears | `backend/core/interview.py` | `chat()` method — `_turn_count >= 3` threshold |
| What profile fields are extracted | `backend/core/interview.py` | `_EXTRACT_PROMPT` constant |
| Accepted values for goal / subject / device | `backend/models/profile.py` | `PrimaryGoal`, `PrimarySubject`, `DeviceType` literals |
| The 6 visual style options | `backend/core/interview.py` + `camera-protoype/src/components/StyleGrid.tsx` | `_STYLE_NAMES` list (backend) and `STYLES` array (frontend) — keep in sync |

---

### Teaching strategy & feedback quality

| What you want to change | Where to go | What to look for |
|---|---|---|
| How feedback is written (tone, structure) | `backend/core/teacher.py` | `_FEEDBACK_SYSTEM` + `_FEEDBACK_PROMPT` constants |
| How gap analysis works (skill vs vision vs mixed) | `backend/core/teacher.py` | `_GAP_SYSTEM` + `_GAP_PROMPT` + `_analyse_gap()` |
| How feedback is converted to natural prose | `backend/core/teacher.py` | `_PROSE_SYSTEM` + `_PROSE_PROMPT` + `_to_prose()` |
| What concept and assignment the planner generates | `backend/core/planner.py` | `_SYSTEM` + `_PROMPT_TEMPLATE` constants |
| What dimensions the evaluator analyses | `backend/core/evaluator.py` | `_SYSTEM` + `_PROMPT_TEMPLATE` + `_DIMENSION_KEYS` |

---

### Progression & gamification

| What you want to change | Where to go | What to look for |
|---|---|---|
| Milestone thresholds (Developing / Intermediate / Advanced) | `backend/models/teaching.py` | `compute_milestone()` function |
| Skill level descriptions (what each 1–5 means) | `backend/models/teaching.py` | `LEVEL_DESCRIPTIONS` dict |
| Advancement rule (currently 2 advances in last 3 attempts) | `backend/core/progression.py` | `should_advance()` on `SkillDimension` in `backend/models/profile.py` |
| Stuck protocol threshold (currently 3 consecutive retries) | `backend/models/profile.py` | `is_stuck()` on `SkillDimension` |
| Simplified fallback assignments when stuck | `backend/models/teaching.py` | `FALLBACK_ASSIGNMENTS` dict |
| Target skill selection priority order | `backend/core/progression.py` | `select_target_skill()` + `_CORE_DIMENSIONS` |
| Advance / retry / guided retry decision logic | `backend/core/progression.py` | `decide_attempt_result()` |
| What `recommended_action` maps to in the UI | `camera-protoype/src/pages/Teaching.tsx` | `ACTION_LABELS` constant |

---

### Live camera guidance

| What you want to change | Where to go | What to look for |
|---|---|---|
| Skill-specific rotating tips | `camera-protoype/src/components/Camera.tsx` | `SKILL_TIPS` constant |
| Brightness warning thresholds | `camera-protoype/src/components/Camera.tsx` | Brightness analysis `useEffect` — `< 45` and `> 215` values |
| Tilt sensitivity | `camera-protoype/src/components/Camera.tsx` | Tilt cue `useEffect` — `Math.abs(tiltAngle) > 8` threshold |
| Tip rotation interval | `camera-protoype/src/components/Camera.tsx` | `setInterval(..., 5000)` in rotating tips `useEffect` |
| Rule-of-thirds grid style | `camera-protoype/src/components/Camera.tsx` | Grid overlay JSX block |
| Replace basic cues with real CV detection | `camera-protoype/src/components/Camera.tsx` | Replace brightness + tilt `useEffect` blocks with CV model calls |

---

### Adding or removing skill dimensions

Touching more than one file — this is the one change that crosses boundaries:

1. `backend/models/profile.py` — add/remove field on `SkillState`
2. `backend/models/teaching.py` — add/remove entry in `LEVEL_DESCRIPTIONS`, `SKILL_DEFINITIONS`, `FALLBACK_ASSIGNMENTS`
3. `backend/models/session.py` — add/remove status field on `FinalCaptureState` and value in `TargetSkill` literal
4. `camera-protoype/src/types/index.ts` — update `TargetSkill` type and `SKILL_LABELS` in `SkillProgress.tsx`
5. `camera-protoype/src/components/Camera.tsx` — update `SKILL_TIPS` and `CUE_TO_DETAIL`

---

### LLM providers and models

| What you want to change | Where to go |
|---|---|
| Switch text LLM (OpenAI ↔ Gemini) | `.env` — set `TEXT_LLM_PROVIDER=gemini` |
| Switch vision LLM | `.env` — set `VISION_LLM_PROVIDER=openai` or `qwen_local` |
| Change specific model name | `.env` — `TEXT_MODEL=` or `VISION_MODEL=` |
| Add a new LLM provider | `backend/core/llm.py` — add `_newprovider_text()` and wire into `call_text()` |
| Add local/offline model support | `backend/core/llm.py` — same pattern as `qwen_local` branch |

---

### Storage and persistence

| What you want to change | Where to go | What to look for |
|---|---|---|
| Profile storage location | `backend/core/storage.py` | `_PROFILES_DIR` constant |
| Switch from JSON files to a database | `backend/core/storage.py` | Replace `save_profile()` and `load_profile()` — nothing else needs to change |
| Session persistence (currently in-memory only) | `backend/api/sessions.py` | Replace the dicts with a persistent store |

---

## LLM providers

| Component | Provider options |
|---|---|
| Text (interview, feedback, planning) | OpenAI `gpt-4o-mini` · Google `gemini-2.5-flash` |
| Vision (photo evaluation) | OpenAI `gpt-4o` · Qwen2.5-VL-3B (local) |

---

## Setup

### Backend

**1. Clone and create environment**
```bash
git clone git@github.com:ShadowsKuming/photography-teaching-system.git
cd photography-teaching-system
conda env create -f environment.yml
conda activate photography-teaching
```

**2. Add API keys**

Copy the example and fill in your keys:
```bash
cp .env.example .env
```

```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...        # optional, only if TEXT_LLM_PROVIDER=gemini
TEXT_LLM_PROVIDER=openai
VISION_LLM_PROVIDER=openai
```

**3. Run the backend**
```bash
uvicorn backend.api.app:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

---

### Frontend

```bash
cd camera-protoype
npm install
npm run dev
```

Open `http://localhost:5173`

For native iOS/Android:
```bash
npm run cap:sync
npm run cap:open:ios      # opens Xcode
npm run cap:open:android  # opens Android Studio
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Server status and active providers |
| `POST` | `/interview/start` | Create interview session, return opening message |
| `POST` | `/interview/{id}/chat` | Send student message, get reply |
| `POST` | `/interview/{id}/style` | Submit style grid selection |
| `POST` | `/interview/{id}/name` | Submit student name, complete interview |
| `POST` | `/interview/{id}/complete` | Extract and persist `UserProfile` |
| `POST` | `/teach/start` | Load profile, create teaching session, return first lesson |
| `POST` | `/teach/{id}/submit` | Submit photo + live context, return `SessionBlockResult` |
| `POST` | `/teach/{id}/next` | Advance to next lesson plan |
| `GET` | `/teach/{id}/profile` | Current profile and skill state |
| `GET` | `/profiles` | List all saved student profiles |
| `GET` | `/profiles/{name}` | Get a profile by name |
| `DELETE` | `/profiles/{name}` | Delete a profile |
