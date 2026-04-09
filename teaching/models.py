"""
teaching/models.py
------------------
Shared data structures for the teaching agent system.
No LLM logic here — pure data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ------------------------------------------------------------------ #
#  Evaluator output                                                   #
# ------------------------------------------------------------------ #

@dataclass
class DimensionObservation:
    """
    One dimension of a photo, described factually.
    No scores, no teaching language, no judgement.
    """
    dimension:   str   # "light" | "composition" | "color" |
                       # "subject_clarity" | "moment_storytelling"
    observation: str   # what was seen
    is_focus:    bool  # True if this was the dimension being practiced


@dataclass
class EvaluationReport:
    """
    Objective visual analysis produced by the AssignmentEvaluationAssistant.
    Contains observations only — the Teacher interprets them.
    """
    dimensions:  List[DimensionObservation]
    summary:     str            # one paragraph, objective
    vs_previous: Optional[str]  # factual comparison with last submission,
                                # or None for first submission

    def get(self, dimension: str) -> Optional[DimensionObservation]:
        for d in self.dimensions:
            if d.dimension == dimension:
                return d
        return None

    def focus_observation(self) -> Optional[DimensionObservation]:
        for d in self.dimensions:
            if d.is_focus:
                return d
        return None


# ------------------------------------------------------------------ #
#  Planner output                                                     #
# ------------------------------------------------------------------ #

@dataclass
class LessonPlan:
    """
    Recommendation from the LessonPlanningAssistant.
    The Teacher makes the final decision — this is input, not instruction.
    """
    concept:         str   # what principle to teach this phase
    assignment:      str   # concrete task for the user
    focus_dimension: str   # which skill dimension this targets
    rationale:       str   # why this, given profile + history


# ------------------------------------------------------------------ #
#  Teacher internals                                                  #
# ------------------------------------------------------------------ #

@dataclass
class GapAnalysis:
    """
    Produced by the Teacher after receiving an EvaluationReport.
    Answers: does the photo serve intent? does it address the assignment?
    What's in the way, and what kind of gap is it?
    """
    what_works:           List[str]
    primary_gap:          str
    gap_type:             str   # "skill" | "vision" | "mixed"
    gap_reasoning:        str   # why this type — shapes feedback tone
    intent_alignment:     str   # does photo serve photographic_intent?
    assignment_alignment: str   # does photo address the assignment?


@dataclass
class FeedbackMessage:
    """
    Structured feedback produced by the Teacher.
    Enforces: one focus, principle over symptom, connected to intent.
    """
    acknowledgment:    str   # what landed — specific and genuine
    primary_focus:     str   # ONE issue only
    principle:         str   # underlying concept, not surface symptom
    intent_connection: str   # explicit link to user's photographic goal
    next_exercise:     str   # concrete and specific


# ------------------------------------------------------------------ #
#  Skill observation — slow update model                             #
# ------------------------------------------------------------------ #

@dataclass
class SkillObservation:
    """
    One observed signal for one dimension in one session.
    Skill scores only update after 2-3 consistent signals.
    """
    session_n: int
    dimension: str
    signal:    str   # "strong" | "developing" | "struggling"
    note:      str   # brief evidence


# ------------------------------------------------------------------ #
#  Phase and step enums                                               #
# ------------------------------------------------------------------ #

class TeachingPhase(Enum):
    BASELINE   = "baseline"
    TEACHING   = "teaching"
    REFLECTING = "reflecting"
    COMPLETED  = "completed"


class InternalStep(Enum):
    """
    Sub-steps within TEACHING phase.
    Internal tracking only — not exposed in UI.
    """
    PLANNING         = "planning"
    EXPLAINING       = "explaining"
    AWAITING_PHOTO   = "awaiting_photo"
    AWAITING_INTENT  = "awaiting_intent"
    EVALUATING       = "evaluating"
    DELIVERING       = "delivering"


# ------------------------------------------------------------------ #
#  Teacher turn output                                                #
# ------------------------------------------------------------------ #

@dataclass
class TurnResult:
    reply:            str
    phase:            TeachingPhase
    show_upload:      bool   # UI hint: show image upload widget
    session_complete: bool
