"""
teaching/teacher.py
-------------------
TeacherAgent — the orchestrator and sole user-facing component.

Responsibilities:
  - Conversing with the user (teaching, guiding, feedback)
  - Deciding what to do next (explain / assign / review)
  - Interpreting evaluation results → gap analysis
  - Generating feedback (one focus, principle, intent-connected)
  - Updating student memory and skill model
  - Deciding when to advance the topic or complete the session

Assistants are called internally. The Teacher makes all final decisions.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from PIL import Image

from teaching.evaluator import AssignmentEvaluationAssistant
from teaching.models import (
    EvaluationReport, FeedbackMessage, GapAnalysis,
    InternalStep, LessonPlan, SkillObservation,
    TeachingPhase, TurnResult,
)
from teaching.planner import LessonPlanningAssistant
from interview.profile import SessionRecord, SkillModel, UserProfile

load_dotenv()

# ------------------------------------------------------------------ #
#  System prompt                                                      #
# ------------------------------------------------------------------ #

_TEACHER_SYSTEM = """\
You are a photography teacher — warm, direct, and pedagogically intentional.
You are having a one-on-one teaching session with a student.

Your student's profile:
{profile_context}

Current lesson plan:
  Concept        : {concept}
  Assignment     : {assignment}
  Focus dimension: {focus_dimension}

Teaching principles you must follow:

1. INTENT FIRST — always connect feedback to what the student wants to express.
   Never give generic technique advice divorced from their goal.

2. ONE FOCUS — in any feedback turn, address ONE issue only.
   Never list multiple problems. If you see five issues, pick the most important one.

3. TEACH THE PRINCIPLE — explain why something matters, not just what to change.
   ❌ "Your light is flat"
   ✅ "The flat light removes shadows, which removes depth — and depth is what gives
       the viewer a sense of presence in the scene you wanted to create"

4. NAME THE GAP TYPE:
   - skill gap  → execution issue. Teach the technique or decision.
   - vision gap → they didn't see the opportunity. Teach how to pre-visualise.
   - mixed      → address vision first, then technique.

5. ACKNOWLEDGE BEFORE CRITIQUING — always open with something genuine that worked.

6. TONE — warm and direct. Not overly encouraging. Not harsh.
   Treat the student as capable. Expect effort.

Current phase: {phase}"""


# ------------------------------------------------------------------ #
#  Gap analysis prompt                                                #
# ------------------------------------------------------------------ #

_GAP_PROMPT = """\
You are analysing the gap between a student's photographic intent and their submission.

Student's photographic intent (from their profile):
  "{photographic_intent}"

What the student said they were going for with THIS photo:
  "{shot_intent}"

What the assignment asked for:
  "{assignment}"

What the photo actually shows (evaluation report):
{eval_observations}

---

Analyze the gap across two axes:

1. Intent alignment — does the photo serve what the student always wants to express?
2. Assignment alignment — does the photo address what was assigned?

Then identify:
  - what_works (list, 1-3 specific things)
  - primary_gap (the single most important gap)
  - gap_type: "skill" | "vision" | "mixed"
     skill  = they understood what to do but execution fell short (technique, timing, settings)
     vision = they didn't see the opportunity when shooting (pre-visualisation, noticing)
     mixed  = both
  - gap_reasoning: why this type

Return ONLY valid JSON:
{{
  "what_works": ["...", "..."],
  "primary_gap": "...",
  "gap_type": "skill | vision | mixed",
  "gap_reasoning": "...",
  "intent_alignment": "...",
  "assignment_alignment": "..."
}}"""


# ------------------------------------------------------------------ #
#  Feedback generation prompt                                         #
# ------------------------------------------------------------------ #

_FEEDBACK_PROMPT = """\
You are generating structured teaching feedback.

Student profile:
  photographic_intent: "{photographic_intent}"
  visual_references:   "{visual_references}"
  inferred_level:      {inferred_level}

Gap analysis:
  what_works:           {what_works}
  primary_gap:          "{primary_gap}"
  gap_type:             {gap_type}
  gap_reasoning:        "{gap_reasoning}"
  intent_alignment:     "{intent_alignment}"

Current focus dimension: {focus_dimension}

---

Generate feedback with these five components:

1. acknowledgment   — one specific, genuine thing that worked. Not generic praise.
2. primary_focus    — the ONE gap to address. Stated clearly without softening.
3. principle        — the underlying concept behind this gap. Why does it matter?
                      Connect it to the student's intent, not abstract technique.
4. intent_connection— explicitly bridge: "this matters because you want to express X"
5. next_exercise    — one concrete, specific exercise.
                      Must be achievable, must target this exact gap.

Calibrate depth and vocabulary to inferred_level {inferred_level}/5.
  Level 1-2: simple language, one idea at a time
  Level 3-4: introduce correct terminology, more nuance
  Level 5:   peer-level, assume full vocabulary

{gap_type_instruction}

Return ONLY valid JSON:
{{
  "acknowledgment":    "...",
  "primary_focus":     "...",
  "principle":         "...",
  "intent_connection": "...",
  "next_exercise":     "..."
}}"""

_GAP_TYPE_INSTRUCTIONS = {
    "skill":  "This is a skill gap — teach the technique or decision that would close it.",
    "vision": "This is a vision gap — teach how to see and pre-visualise this before shooting. "
              "The exercise should happen before the camera is raised.",
    "mixed":  "This is a mixed gap — address vision first (what to notice), "
              "then technique (how to capture it). Two steps, in that order.",
}


# ------------------------------------------------------------------ #
#  Objective assessment prompt                                        #
# ------------------------------------------------------------------ #

_OBJECTIVE_PROMPT = """\
A photography teacher is deciding whether to advance the student to a new concept.

Focus dimension being practiced: {focus_dimension}
Teaching concept: "{concept}"

Recent skill observations for this dimension:
{observations}

Has the student demonstrated sufficient grasp of this concept
to move on to something new?

Respond with ONLY valid JSON:
{{
  "advance": true or false,
  "reasoning": "one sentence"
}}"""


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #

def _format_eval_for_prompt(report: EvaluationReport) -> str:
    lines = []
    for d in report.dimensions:
        marker = " ← (focus dimension)" if d.is_focus else ""
        lines.append(f"  {d.dimension}{marker}:\n    {d.observation}")
    if report.vs_previous:
        lines.append(f"\n  vs previous submission:\n    {report.vs_previous}")
    return "\n".join(lines)


def _format_obs_for_prompt(obs: List[SkillObservation], dimension: str) -> str:
    relevant = [o for o in obs if o.dimension == dimension][-4:]
    if not relevant:
        return "  (no observations yet)"
    return "\n".join(
        f"  session {o.session_n}: {o.signal} — {o.note}"
        for o in relevant
    )


# ------------------------------------------------------------------ #
#  TeacherAgent                                                       #
# ------------------------------------------------------------------ #

class TeacherAgent:

    def __init__(
        self,
        profile:            UserProfile,
        provider:           str = "openai",
        eval_provider:      str = "openai",   # "openai" | "qwen"
        profile_dir:        str = "profiles",
    ):
        self.profile      = profile
        self.provider     = provider
        self.profile_dir  = profile_dir

        self._evaluator   = AssignmentEvaluationAssistant(provider=eval_provider)
        self._planner     = LessonPlanningAssistant(provider=provider)

        # Session state
        self.phase:         TeachingPhase      = TeachingPhase.BASELINE
        self.step:          InternalStep       = InternalStep.PLANNING
        self.session_n:     int                = len(profile.performance_history) + 1
        self.skill_obs:     List[SkillObservation]    = []
        self.current_plan:  Optional[LessonPlan]      = None
        self.prev_report:   Optional[EvaluationReport]= None
        self.pending_image: Optional[Image.Image]     = None
        self.pending_intent: Optional[str]            = None

        # Conversation history
        self._history: List[dict] = []

    # ---------------------------------------------------------------- #
    #  LLM generation                                                   #
    # ---------------------------------------------------------------- #

    def _generate(
        self,
        messages:    List[dict],
        temperature: float = 0.7,
        max_tokens:  int   = 400,
    ) -> str:
        if self.provider == "openai":
            from openai import OpenAI
            client   = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            response = client.chat.completions.create(
                model       = "gpt-4o-mini",
                messages    = messages,
                temperature = temperature,
                max_tokens  = max_tokens,
            )
            return response.choices[0].message.content.strip()

        from google import genai
        from google.genai import types
        client     = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        contents   = [
            types.Content(role=m["role"], parts=[types.Part(text=m["content"])])
            for m in messages if m["role"] != "system"
        ]
        resp = client.models.generate_content(
            model    = "gemini-2.5-flash",
            contents = contents,
            config   = types.GenerateContentConfig(
                system_instruction = system_msg,
                temperature        = temperature,
                max_output_tokens  = max_tokens,
            ),
        )
        return resp.text.strip()

    def _llm_json(self, prompt: str, max_tokens: int = 400) -> dict:
        raw     = self._generate(
            [{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=max_tokens,
        )
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        match   = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}

    # ---------------------------------------------------------------- #
    #  System prompt builder                                            #
    # ---------------------------------------------------------------- #

    def _system_prompt(self) -> str:
        plan = self.current_plan
        return _TEACHER_SYSTEM.format(
            profile_context = self.profile.to_teacher_context(),
            concept         = plan.concept         if plan else "(not yet set)",
            assignment      = plan.assignment      if plan else "(not yet set)",
            focus_dimension = plan.focus_dimension if plan else "(not yet set)",
            phase           = self.phase.value,
        )

    def _chat_reply(
        self,
        user_message: Optional[str] = None,
        temperature:  float         = 0.75,
        max_tokens:   int           = 350,
    ) -> str:
        messages = [{"role": "system", "content": self._system_prompt()}]
        messages += self._history
        if user_message:
            messages.append({"role": "user", "content": user_message})
        reply = self._generate(messages, temperature=temperature, max_tokens=max_tokens)
        if user_message:
            self._history.append({"role": "user",      "content": user_message})
        self._history.append(    {"role": "assistant", "content": reply})
        return reply

    # ---------------------------------------------------------------- #
    #  Gap analysis                                                     #
    # ---------------------------------------------------------------- #

    def _analyze_gap(
        self,
        report:      EvaluationReport,
        shot_intent: Optional[str],
    ) -> GapAnalysis:
        data = self._llm_json(
            _GAP_PROMPT.format(
                photographic_intent = self.profile.photographic_intent or "(not stated)",
                shot_intent         = shot_intent or "(not stated)",
                assignment          = self.current_plan.assignment if self.current_plan else "(none)",
                eval_observations   = _format_eval_for_prompt(report),
            ),
            max_tokens=400,
        )
        return GapAnalysis(
            what_works           = data.get("what_works",           []),
            primary_gap          = data.get("primary_gap",          ""),
            gap_type             = data.get("gap_type",             "skill"),
            gap_reasoning        = data.get("gap_reasoning",        ""),
            intent_alignment     = data.get("intent_alignment",     ""),
            assignment_alignment = data.get("assignment_alignment", ""),
        )

    # ---------------------------------------------------------------- #
    #  Feedback generation                                              #
    # ---------------------------------------------------------------- #

    def _generate_feedback(self, gap: GapAnalysis) -> FeedbackMessage:
        plan = self.current_plan
        data = self._llm_json(
            _FEEDBACK_PROMPT.format(
                photographic_intent  = self.profile.photographic_intent or "(not stated)",
                visual_references    = self.profile.visual_references   or "(none)",
                inferred_level       = self.profile.inferred_level,
                what_works           = gap.what_works,
                primary_gap          = gap.primary_gap,
                gap_type             = gap.gap_type,
                gap_reasoning        = gap.gap_reasoning,
                intent_alignment     = gap.intent_alignment,
                focus_dimension      = plan.focus_dimension if plan else "light",
                gap_type_instruction = _GAP_TYPE_INSTRUCTIONS.get(gap.gap_type, ""),
            ),
            max_tokens=500,
        )
        return FeedbackMessage(
            acknowledgment    = data.get("acknowledgment",    ""),
            primary_focus     = data.get("primary_focus",     ""),
            principle         = data.get("principle",         ""),
            intent_connection = data.get("intent_connection", ""),
            next_exercise     = data.get("next_exercise",     ""),
        )

    def _feedback_to_prose(self, fb: FeedbackMessage) -> str:
        """Convert structured feedback into a single natural conversational message."""
        prompt = f"""\
Convert this structured feedback into a single natural teaching message.
Write as the teacher speaking directly to the student.
Keep the structure: acknowledge → focus → principle → intent connection → exercise.
Do NOT add section headers. Do NOT use bullet points. Flowing prose only.
Warm but direct. Maximum 200 words.

acknowledgment    : {fb.acknowledgment}
primary_focus     : {fb.primary_focus}
principle         : {fb.principle}
intent_connection : {fb.intent_connection}
next_exercise     : {fb.next_exercise}"""

        return self._generate(
            [{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=300,
        )

    # ---------------------------------------------------------------- #
    #  Skill observation + model update                                 #
    # ---------------------------------------------------------------- #

    def _record_observation(self, gap: GapAnalysis):
        """Record one signal for the focus dimension. Don't update scores yet."""
        if not self.current_plan:
            return
        signal_map = {"skill": "developing", "vision": "struggling", "mixed": "developing"}
        # Infer signal: if what_works mentions focus dim, lean stronger
        focus   = self.current_plan.focus_dimension
        obs_txt = next(
            (d.observation for d in (self.prev_report.dimensions if self.prev_report else [])
             if d.dimension == focus), ""
        )
        # Simple heuristic: if primary_gap doesn't mention the focus dim, it's stronger
        if focus.lower() not in gap.primary_gap.lower():
            signal = "strong"
        else:
            signal = signal_map.get(gap.gap_type, "developing")

        self.skill_obs.append(SkillObservation(
            session_n = self.session_n,
            dimension = focus,
            signal    = signal,
            note      = gap.primary_gap[:120],
        ))

    def _update_skill_model_if_consistent(self):
        """Only update numeric scores after 2-3 consistent signals."""
        sm    = self.profile.skill_model
        dims  = ["composition", "lighting", "color", "subject_clarity",
                 "technical_use", "moment_storytelling", "post_processing"]
        dim_map = {
            "light":               "lighting",
            "composition":         "composition",
            "color":               "color",
            "subject_clarity":     "subject_clarity",
            "moment_storytelling": "moment_storytelling",
        }
        for obs_dim, model_dim in dim_map.items():
            recent  = [o for o in self.skill_obs if o.dimension == obs_dim][-3:]
            if len(recent) < 2:
                continue
            signals = [o.signal for o in recent]
            current = getattr(sm, model_dim) or 1.0
            if all(s == "strong" for s in signals):
                setattr(sm, model_dim, min(5.0, current + 0.5))
            elif all(s == "struggling" for s in signals):
                setattr(sm, model_dim, max(1.0, current - 0.5))

    # ---------------------------------------------------------------- #
    #  Objective check                                                  #
    # ---------------------------------------------------------------- #

    def _should_advance(self) -> bool:
        if not self.current_plan:
            return False
        data = self._llm_json(
            _OBJECTIVE_PROMPT.format(
                focus_dimension = self.current_plan.focus_dimension,
                concept         = self.current_plan.concept,
                observations    = _format_obs_for_prompt(
                    self.skill_obs, self.current_plan.focus_dimension
                ),
            ),
            max_tokens=100,
        )
        return bool(data.get("advance", False))

    # ---------------------------------------------------------------- #
    #  Session record                                                   #
    # ---------------------------------------------------------------- #

    def _save_session(self, fb: FeedbackMessage):
        if not self.current_plan:
            return
        record = SessionRecord(
            date                  = datetime.now().isoformat(),
            images_reviewed       = ["submitted photo"],
            skills_exercised      = [self.current_plan.focus_dimension],
            teacher_recommendations = [fb.next_exercise],
            notes                 = f"gap_type={self._last_gap_type} | "
                                    f"{self.current_plan.concept[:80]}",
        )
        self.profile.performance_history.append(record)
        self.profile.save(self.profile_dir)

    # ---------------------------------------------------------------- #
    #  Public API                                                       #
    # ---------------------------------------------------------------- #

    def start(self) -> TurnResult:
        """Open the session. Returns the teacher's opening message."""
        if self.session_n == 1:
            reply = self._chat_reply(
                user_message=None,
                temperature=0.7,
                max_tokens=200,
            )
            # Inject opening instruction without calling chat
            self._history = []
            opening_prompt = (
                f"[session_start: This is the student's first session. "
                f"Greet them warmly and briefly. "
                f"Explain that you'd like to start by seeing a photo they've taken recently "
                f"— anything at all, so you can understand where they are right now. "
                f"Keep it to 2-3 sentences. Do not explain the whole plan.]"
            )
            reply = self._chat_reply(user_message=opening_prompt)
            # Remove the system note from visible history
            self._history = [m for m in self._history if not m["content"].startswith("[session_start")]
            self.phase = TeachingPhase.BASELINE
            return TurnResult(reply=reply, phase=self.phase,
                              show_upload=True, session_complete=False)

        # Returning session
        self.current_plan = self._planner(
            self.profile, self.skill_obs, self.session_n, None
        )
        self.phase = TeachingPhase.TEACHING
        self.step  = InternalStep.EXPLAINING
        prompt = (
            f"[session_start: Returning student, session {self.session_n}. "
            f"Welcome them back briefly. "
            f"The plan for today is: {self.current_plan.concept}. "
            f"Introduce this concept naturally in 2-3 sentences.]"
        )
        reply = self._chat_reply(user_message=prompt)
        self._history = [m for m in self._history if not m["content"].startswith("[session_start")]
        return TurnResult(reply=reply, phase=self.phase,
                          show_upload=False, session_complete=False)

    def chat(
        self,
        user_message: str,
        image:        Optional[Image.Image] = None,
    ) -> TurnResult:
        """Main turn handler. Routes to the correct phase/step."""

        # ── BASELINE ────────────────────────────────────────────────
        if self.phase == TeachingPhase.BASELINE:
            if image is None:
                reply = self._chat_reply(user_message)
                return TurnResult(reply, self.phase, show_upload=True,
                                  session_complete=False)

            # Baseline photo received — brief evaluation, no deep critique
            report = self._evaluator(
                image, shot_intent=None, prev_report=None, focus_dim="light"
            )
            self.prev_report = report

            # Get plan now that we have baseline
            self.current_plan = self._planner(
                self.profile, self.skill_obs, self.session_n, None
            )

            prompt = (
                f"[baseline_received: Briefly acknowledge what you saw in 1-2 sentences. "
                f"Factual, not detailed critique. Then introduce today's concept: "
                f"'{self.current_plan.concept}'. "
                f"Keep total response to 3-4 sentences.]"
            )
            reply = self._chat_reply(user_message=prompt)
            self._history = [m for m in self._history
                             if not m["content"].startswith("[baseline_received")]
            self.phase = TeachingPhase.TEACHING
            self.step  = InternalStep.EXPLAINING
            return TurnResult(reply, self.phase, show_upload=False,
                              session_complete=False)

        # ── TEACHING — EXPLAINING ────────────────────────────────────
        if self.phase == TeachingPhase.TEACHING and self.step == InternalStep.EXPLAINING:
            # User asking a question or chatting — keep teaching
            # Check if user is ready to try / submit something
            ready_signals = {"ready", "try", "go", "shoot", "ok", "sure",
                             "sounds good", "got it", "let me try", "understand"}
            if any(s in user_message.lower() for s in ready_signals) or len(user_message.split()) <= 4:
                prompt = (
                    f"[assign_now: The student seems ready. Give the assignment clearly: "
                    f"'{self.current_plan.assignment}'. "
                    f"Be specific and brief. End by asking them to submit their photo when ready.]"
                )
                reply = self._chat_reply(user_message=prompt)
                self._history = [m for m in self._history
                                 if not m["content"].startswith("[assign_now")]
                self.step = InternalStep.AWAITING_PHOTO
                return TurnResult(reply, self.phase, show_upload=True,
                                  session_complete=False)

            reply = self._chat_reply(user_message)
            return TurnResult(reply, self.phase, show_upload=False,
                              session_complete=False)

        # ── TEACHING — AWAITING PHOTO ────────────────────────────────
        if self.phase == TeachingPhase.TEACHING and self.step == InternalStep.AWAITING_PHOTO:
            if image is None:
                reply = self._chat_reply(user_message)
                return TurnResult(reply, self.phase, show_upload=True,
                                  session_complete=False)

            self.pending_image = image
            prompt = (
                "[photo_received: Acknowledge the photo simply in one sentence. "
                "Then ask: what were you going for with this one? "
                "Keep it very brief and natural.]"
            )
            reply = self._chat_reply(user_message=prompt)
            self._history = [m for m in self._history
                             if not m["content"].startswith("[photo_received")]
            self.step = InternalStep.AWAITING_INTENT
            return TurnResult(reply, self.phase, show_upload=False,
                              session_complete=False)

        # ── TEACHING — AWAITING INTENT ───────────────────────────────
        if self.phase == TeachingPhase.TEACHING and self.step == InternalStep.AWAITING_INTENT:
            self.pending_intent = user_message

            # Evaluate
            report = self._evaluator(
                self.pending_image,
                shot_intent  = self.pending_intent,
                prev_report  = self.prev_report,
                focus_dim    = self.current_plan.focus_dimension,
            )

            # Gap analysis
            gap = self._analyze_gap(report, self.pending_intent)
            self._last_gap_type = gap.gap_type

            # Feedback
            fb    = self._generate_feedback(gap)
            prose = self._feedback_to_prose(fb)

            # Add to history naturally
            self._history.append({"role": "assistant", "content": prose})

            # Record
            self._record_observation(gap)
            self._save_session(fb)
            self.prev_report = report
            self.session_n  += 1

            self.phase = TeachingPhase.REFLECTING
            return TurnResult(prose, self.phase, show_upload=False,
                              session_complete=False)

        # ── REFLECTING ───────────────────────────────────────────────
        if self.phase == TeachingPhase.REFLECTING:
            # Check if session should end or advance
            advance = self._should_advance()

            if advance:
                self._update_skill_model_if_consistent()
                new_plan = self._planner(
                    self.profile, self.skill_obs,
                    self.session_n, self.current_plan,
                )
                self.current_plan = new_plan
                prompt = (
                    f"[advance_topic: The student has made sufficient progress on "
                    f"'{self.current_plan.focus_dimension}'. "
                    f"Briefly acknowledge the progress. "
                    f"Introduce the next concept: '{self.current_plan.concept}'. "
                    f"Natural transition, 2-3 sentences.]"
                )
                reply = self._chat_reply(user_message=prompt)
                self._history = [m for m in self._history
                                 if not m["content"].startswith("[advance_topic")]
                self.phase = TeachingPhase.TEACHING
                self.step  = InternalStep.EXPLAINING
                return TurnResult(reply, self.phase, show_upload=False,
                                  session_complete=False)

            # Continue reflecting — answer questions, then offer another attempt
            reply = self._chat_reply(user_message)

            # After reflection exchange, offer next attempt
            offer_prompt = (
                "[offer_attempt: After engaging with the student's question, "
                "offer to try again with the same assignment. "
                "Brief, encouraging, ends with a gentle invitation to shoot again.]"
            )
            offer = self._chat_reply(user_message=offer_prompt)
            self._history = [m for m in self._history
                             if not m["content"].startswith("[offer_attempt")]
            combined = reply + "\n\n" + offer
            self.phase = TeachingPhase.TEACHING
            self.step  = InternalStep.AWAITING_PHOTO
            return TurnResult(combined, self.phase, show_upload=True,
                              session_complete=False)

        # ── COMPLETED ────────────────────────────────────────────────
        reply = self._chat_reply(user_message)
        return TurnResult(reply, self.phase, show_upload=False,
                          session_complete=True)
