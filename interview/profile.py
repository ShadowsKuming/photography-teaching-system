from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime
import json
import os


# ------------------------------------------------------------------ #
#  Skill model — all None until assessed during first class           #
# ------------------------------------------------------------------ #

@dataclass
class SkillModel:
    composition:        Optional[float] = None  # 1–5
    lighting:           Optional[float] = None
    color:              Optional[float] = None
    subject_clarity:    Optional[float] = None
    technical_use:      Optional[float] = None
    moment_storytelling: Optional[float] = None
    post_processing:    Optional[float] = None


# ------------------------------------------------------------------ #
#  Session record — appended after each teaching session              #
# ------------------------------------------------------------------ #

@dataclass
class SessionRecord:
    date: str
    images_reviewed: List[str] = field(default_factory=list)   # file paths or descriptions
    skills_exercised: List[str] = field(default_factory=list)
    teacher_recommendations: List[str] = field(default_factory=list)
    notes: str = ""                                             # breakthroughs, repeated mistakes


# ------------------------------------------------------------------ #
#  Core user profile                                                  #
# ------------------------------------------------------------------ #

@dataclass
class UserProfile:
    # -- base info (filled by interview agent) --
    name: str = "Anonymous"
    photographic_intent: str = ""        # abstracted emotional/expressive goal
    subject_world: str = ""              # general type of subjects/atmospheres they gravitate toward
    teaching_direction: str = ""         # what skill area to focus on first
    device: str = "unknown"              # smartphone | entry-DSLR | mirrorless | film
    visual_references: str = ""          # aesthetic anchors — photographers, films, vibes
    inferred_level: int = 1              # 1–5, hidden from user, estimated from conversation

    # -- skill model (null until first class) --
    skill_model: SkillModel = field(default_factory=SkillModel)

    # -- performance history --
    performance_history: List[SessionRecord] = field(default_factory=list)

    # -- metadata --
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # ------------------------------------------------------------------ #
    #  Persistence                                                         #
    # ------------------------------------------------------------------ #

    def save(self, profile_dir: str = "profiles") -> str:
        os.makedirs(profile_dir, exist_ok=True)
        self.updated_at = datetime.now().isoformat()
        slug = self.name.lower().replace(" ", "_") or "anonymous"
        path = os.path.join(profile_dir, f"{slug}.json")
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        return path

    @classmethod
    def load(cls, name: str, profile_dir: str = "profiles") -> Optional["UserProfile"]:
        slug = name.lower().replace(" ", "_")
        path = os.path.join(profile_dir, f"{slug}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        data["skill_model"] = SkillModel(**data.get("skill_model", {}))
        data["performance_history"] = [
            SessionRecord(**s) for s in data.get("performance_history", [])
        ]
        return cls(**data)

    # ------------------------------------------------------------------ #
    #  RAG interface — returns text chunks ready for embedding            #
    # ------------------------------------------------------------------ #

    def to_rag_chunks(self) -> List[dict]:
        """
        Returns a list of {"id": str, "text": str} dicts.
        Each chunk covers one semantic area so retrieval is precise.
        """
        chunks = []

        chunks.append({
            "id": f"{self.name}::intent",
            "text": (
                f"{self.name}'s photographic intent: {self.photographic_intent}. "
                f"They are drawn to: {self.subject_world}. "
                f"Teaching direction: {self.teaching_direction}."
            )
        })

        aesthetic_parts = []
        if self.visual_references:
            aesthetic_parts.append(f"references: {self.visual_references}")
        if self.subject_world:
            aesthetic_parts.append(f"drawn to: {self.subject_world}")
        if aesthetic_parts:
            chunks.append({
                "id": f"{self.name}::aesthetic",
                "text": (
                    f"{self.name}'s visual aesthetic — "
                    + "; ".join(aesthetic_parts) + "."
                )
            })

        chunks.append({
            "id": f"{self.name}::context",
            "text": (
                f"{self.name} shoots with {self.device}. "
                f"Estimated skill level: {self.inferred_level}/5."
            )
        })

        sm = self.skill_model
        assessed = {k: v for k, v in asdict(sm).items() if v is not None}
        if assessed:
            scores = ", ".join(f"{k.replace('_', ' ')}: {v}/5" for k, v in assessed.items())
            chunks.append({
                "id": f"{self.name}::skills",
                "text": f"{self.name}'s assessed skill scores — {scores}."
            })

        for i, session in enumerate(self.performance_history):
            rec_text = "; ".join(session.teacher_recommendations) or "none"
            chunks.append({
                "id": f"{self.name}::session_{i}",
                "text": (
                    f"Session on {session.date}: reviewed {', '.join(session.images_reviewed) or 'images'}. "
                    f"Skills exercised: {', '.join(session.skills_exercised)}. "
                    f"Recommendations: {rec_text}. Notes: {session.notes}"
                )
            })

        return chunks

    # ------------------------------------------------------------------ #
    #  Teacher agent — direct context injection (no retrieval needed)     #
    # ------------------------------------------------------------------ #

    def to_teacher_context(self) -> str:
        sm = self.skill_model
        assessed = {k: v for k, v in asdict(sm).items() if v is not None}
        skill_str = (
            ", ".join(f"{k.replace('_', ' ')} {v}/5" for k, v in assessed.items())
            if assessed else "not yet assessed"
        )
        return (
            f"Learner: {self.name} | "
            f"Intent: {self.photographic_intent} | "
            f"Subject world: {self.subject_world} | "
            f"Teach first: {self.teaching_direction} | "
            f"Device: {self.device} | "
            f"Aesthetic refs: {self.visual_references or 'not specified'} | "
            f"Level: {self.inferred_level}/5 | "
            f"Skills: {skill_str}"
        )

    def __str__(self) -> str:
        return self.to_teacher_context()
