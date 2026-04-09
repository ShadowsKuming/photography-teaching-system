"""
Interview Agent
---------------
Expression-driven onboarding conversation that builds a UserProfile.
Uses OpenAI or Gemini API. State-aware, two transition modes.

Usage:
    python interview_agent.py [--provider openai|gemini]
"""

import json
import os
import random
import re

from dotenv import load_dotenv

from interview.profile import UserProfile, SkillModel

load_dotenv()

# ------------------------------------------------------------------ #
#  System prompt                                                      #
# ------------------------------------------------------------------ #

INTERVIEW_SYSTEM = """You are a warm, patient teacher having a first conversation with someone \
who may or may not be interested in photography yet.

Your hidden goal is to understand:
- The emotional feeling or mood they want to express (not a specific memory — the deeper intent)
- What subjects, atmospheres, or scenes they gravitate toward
- What visual mood appeals to them
- What device they use (phone or camera) — discover naturally, never interrogate
- Roughly how experienced they are (inferred silently, never asked)

Conversation rules:
- Respond to EMOTIONAL MEANING first — acknowledge before asking anything
- Ask ONE question at a time, short and natural
- Never mention photography or technique until the user has described something they want to express
- NEVER assume the user has already taken a photo unless they explicitly say so
- Do not ask about angle, framing, or settings unless they describe an actual photo
- Do not repeat or re-ask information already given
- Do not stack questions
- NEVER give photography tips or teaching during this conversation

State-specific strategies:
  EXPLORING: user is vague or still discovering
    → open, gentle questions; no pressure; follow their lead

  EXPRESSIVE: user is actively sharing feelings or scenes
    → acknowledge warmly; help them articulate what makes it special
    → once you have emotion + scene + some context, stop probing and summarize

  RESISTANT: user is disengaged or says they don't want to make anything
    → do NOT push photography or creation
    → shift entirely to noticing: "do you ever just find yourself watching these moments?"
    → low-effort, non-committal language; reduce all pressure
    → the goal is awareness, not output

  READY_TO_CREATE: user has shown interest in capturing + enough info exists
    → bridge naturally to photography; ask about their device if not known

STOP + TRANSITION rule — when you receive a system_note about transition:
  full transition: briefly summarize what you understood (1 sentence), reflect as visual \
elements (light, colour, mood), then introduce photography as a natural way to hold that
  soft transition: acknowledge the feeling simply, ask if they ever just notice these \
moments — without needing to do anything with them

Tone and style:
- Warm, calm, unhurried — like a real human teacher, not a chatbot
- You may use a single emoji per message, very sparingly, only when it feels genuinely human
  and fits the moment naturally. Most messages should have no emoji at all.
  Never use emoji decoratively or to signal enthusiasm."""

# ------------------------------------------------------------------ #
#  Prompts                                                            #
# ------------------------------------------------------------------ #

STYLE_SELECTION_PROMPT = """Based on this conversation, choose 2-3 visual photography styles \
that genuinely fit what this person has expressed — their emotional intent, mood, and atmosphere.

Conversation:
{conversation}

Choose ONLY from these exact names:
- Warm & Film
- Clean & Bright
- Moody & Dark
- Documentary
- Soft & Dreamy
- Gritty & Urban

Rules:
- Pick 2-3 styles that match their expressed mood, subjects, or atmosphere
- Exclude styles that clearly clash with what they described
- If the person is vague or resistant, pick the 2 most neutral / broadly fitting options

Return ONLY a valid JSON array of 2-3 names, nothing else.
Example: ["Warm & Film", "Soft & Dreamy"]"""

COVERAGE_PROMPT = """Based on this conversation, assess what we know about the user.

Conversation:
{conversation}

Return ONLY valid JSON:
{{
  "photographic_intent": true or false,
  "subject_world": true or false,
  "device": true or false,
  "visual_aesthetic": true or false,
  "enough": true or false
}}

- photographic_intent: do we know the emotional mood or feeling they want images to carry?
- subject_world: do we know the general type of subjects or atmosphere they gravitate toward?
- device: do we know if they use a phone or camera?
- visual_aesthetic: do we know what mood or style appeals to them?
- enough: true if photographic_intent OR subject_world is true (device and aesthetic are bonuses)"""

EXTRACTION_PROMPT = """Extract a structured photography learner profile from this conversation.
Be faithful — do not invent details. Abstract upward from specific memories to general intent.

Conversation:
{conversation}

Return ONLY valid JSON:
{{
  "name": "what they asked to be called, or 'Anonymous'",
  "photographic_intent": "the overarching emotional goal — what FEELING or MOOD they want \
their images to carry. Abstract from specific memories. \
E.g. not 'rainy day breakup' but 'capturing melancholy and the weight of emotional memory'",
  "subject_world": "general TYPE of subjects and atmospheres — not a specific scene. \
E.g. 'solitary urban moments, weather as emotional metaphor, quiet heavy atmospheres'",
  "teaching_direction": "one sentence: what skill area to focus on first, derived from their intent",
  "device": "their camera or phone, or 'unknown'",
  "visual_references": "ALL named photographers, artists, accounts, films BY NAME plus described \
moods or styles. Empty string if none.",
  "inferred_level": <integer 1-5: 1=total beginner, 2=casual, 3=regular practitioner,
    4=technically skilled, 5=professional. Default to 1 unless clear evidence otherwise.>
}}"""

STATE_ASSESSMENT_PROMPT = """Assess the user's current state in this conversation.

Last 3 user messages:
{recent}

Full conversation context:
{conversation}

Return ONLY valid JSON:
{{
  "state": "exploring" | "expressive" | "resistant" | "ready_to_create",
  "has_emotion": true or false,
  "has_scene": true or false,
  "has_context": true or false,
  "device_known": true or false
}}

State definitions:
- exploring: vague, still discovering, not yet describing anything specific
- expressive: actively sharing feelings, scenes, memories, or desires
- resistant: disengaged, dismissive, says things don't matter or they don't want to make anything
- ready_to_create: has shown clear interest in capturing or making something"""

# ------------------------------------------------------------------ #
#  Fixed messages — never model-generated                            #
# ------------------------------------------------------------------ #

OPENING_MESSAGES = [
    "Hey — is there anything lately you've wanted to capture, express, or share, but weren't sure how?",
    "Is there a moment recently you wished you could hold onto, or show someone exactly as it felt?",
    "Hey — has anything caught your eye lately, something you wanted to keep or pass on somehow?",
    "Is there something you've been wanting to express or share with someone, but couldn't quite find the way?",
    "Have you come across anything recently — a place, a person, a feeling — that you just didn't want to let go of?",
]

NAME_QUESTION = "By the way — what should I call you?"

WRAP_UP_SIGNAL = (
    "[system_note: You now have a good understanding of this person. "
    "Wrap up warmly in 1-2 sentences — do NOT ask for their name, do NOT ask any more questions.]"
)

FULL_TRANSITION_SIGNAL = (
    "[system_note: full_transition — You now have the user's emotion and scene. "
    "STOP asking emotional questions. In your reply: "
    "(1) briefly summarize what you understood — their feeling and scene in 1 sentence, "
    "(2) gently reflect it as visual qualities: light, colour, mood, atmosphere, "
    "(3) introduce photography as a natural way to hold that feeling. "
    "Warm and brief, 2-3 sentences total.]"
)

SOFT_TRANSITION_SIGNAL = (
    "[system_note: soft_transition — This user is resistant to creating or making. "
    "Do NOT mention photography, capturing, or making anything. "
    "Acknowledge their feeling simply in one sentence, then ask: "
    "'do you ever find yourself just noticing these moments — without needing to do anything with them?' "
    "One soft question only.]"
)

STUCK_SIGNAL = (
    "[system_note: stuck_loop — The user keeps giving minimal responses. "
    "STOP asking questions entirely. Write 1 short sentence of validation, then format the "
    "micro-observation exercise as a markdown blockquote (starting with '>') like this:\n"
    "> [exercise text here]\n"
    "The exercise must: use exactly the scene or place they mentioned (streets, light, weather, "
    "whatever they described); ask them to notice ONE small thing — light, colour, or space — "
    "for just a second; end with 'you don't have to do anything with it.' "
    "DO NOT end with a question. No follow-up. Let it land.]"
)

RE_ENTRY_SIGNAL = (
    "[system_note: re_entry — The user has shown a small reaction after the observation exercise. "
    "Treat this as meaningful engagement. "
    "Respond warmly to exactly what they said — acknowledge it genuinely. "
    "You may now gently bridge toward visual expression or photography, but keep it soft. "
    "ONE gentle forward-moving question only. Do not rush.]"
)

# ------------------------------------------------------------------ #
#  Heuristic detection signals                                        #
# ------------------------------------------------------------------ #

def _normalize_text(text: str) -> str:
    """Strip apostrophes/curly-quotes so 'dont' matches 'don't'."""
    return text.replace("'", "").replace("\u2019", "").replace("`", "")

_RESISTANT_SIGNALS = [
    "don't know", "dont know", "doesn't matter", "doesnt matter",
    "not really", "don't care", "dont care", "dont really",
    "not important", "not trying", "unnecessary", "what's the point",
    "just how it", "i wouldn't", "i wouldnt", "not something i", "hard to say",
    "i guess", "kind of empty", "not sure", "doesn't feel", "doesnt feel",
    "never thought", "don't think so", "dont think so", "not interested",
    "whatever", "not much", "i dont", "doesn't matter", "not into",
    "not feeling", "don't feel", "dont feel",
]
_EXPRESSIVE_SIGNALS = [
    "i want to", "i wish", "i feel", "i love", "i remember",
    "it feels like", "i hope", "it reminds me", "i really",
    "beautiful", "amazing", "special", "meaningful", "i'd love",
    "there's something", "i've always",
]
_READY_SIGNALS = [
    "capture", "photograph", "take a photo", "take photos", "shoot",
    "i use", "my phone", "my camera", "i have a camera", "i've tried",
]
_EMOTION_SIGNALS = [
    "feel", "feeling", "emotion", "sad", "happy", "calm", "anxious",
    "empty", "lonely", "peaceful", "nostalgic", "excited", "nervous",
    "miss", "missing", "love", "afraid", "hopeful", "flat", "grey",
    "heavy", "light", "warm", "cold", "quiet", "still",
]
_SCENE_SIGNALS = [
    "sky", "light", "rain", "cloud", "grey", "golden", "dark", "bright",
    "outside", "indoors", "room", "street", "nature", "building", "garden",
    "morning", "evening", "night", "empty", "crowded", "window", "city",
    "sun", "shadow", "colour", "color", "soft", "glow",
]
_DEVICE_SIGNALS = [
    "phone", "camera", "iphone", "android", "samsung", "canon",
    "sony", "nikon", "fuji", "leica", "dslr", "mirrorless",
]

STATE_STRATEGIES = {
    "exploring":      "User is still exploring. Keep questions open and gentle. No pressure toward photography.",
    "expressive":     "User is expressive. Acknowledge warmly, then help articulate the visual feeling.",
    "resistant":      "User is resistant. Do NOT push photography or creation. Shift to noticing. Use low-effort language.",
    "ready_to_create":"User is ready. Bridge naturally to photography. Ask about device if not known.",
    "stuck":          "User is stuck after minimal responses. Do not add more questions. Follow the stuck_loop instruction.",
    "re_entry":       "User is re-engaging after being stuck. Be warm, acknowledge what they said, bridge gently.",
}

# ------------------------------------------------------------------ #
#  Tuning parameters                                                  #
# ------------------------------------------------------------------ #

COVERAGE_CHECK_EVERY   = 3
MIN_TURNS_BEFORE_CHECK = 6
MAX_TURNS              = 20
HARD_STOP_TURN         = 10   # complete regardless at this turn
HEURISTIC_CONFIDENT_THRESHOLD = 2   # signal hits needed to be confident


class InterviewAgent:

    def __init__(self, provider: str = "openai", profile_dir: str = "profiles"):
        self.provider     = provider.lower()
        self.profile_dir  = profile_dir
        self._client      = None

        # session state — reset in start()
        self.history:          list  = []
        self.user_turn_count:  int   = 0
        self.style_grid_shown: bool  = False
        self.is_done:          bool  = False
        self._awaiting_name:   bool  = False
        self._name_collected:  str | None = None
        self._user_state:      str   = "exploring"
        self._transition_done: bool  = False

    # ------------------------------------------------------------------ #
    #  Client init (lazy)                                                 #
    # ------------------------------------------------------------------ #

    def _ensure_client(self):
        if self._client is not None:
            return
        if self.provider == "openai":
            from openai import OpenAI
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY not set in .env")
            self._client = OpenAI(api_key=key)
        elif self.provider == "gemini":
            from google import genai
            key = os.getenv("GEMINI_API_KEY")
            if not key:
                raise ValueError("GEMINI_API_KEY not set in .env")
            self._client = genai.Client(api_key=key)
        else:
            raise ValueError(f"Unknown provider '{self.provider}'. Use 'openai' or 'gemini'.")

    # ------------------------------------------------------------------ #
    #  Core inference                                                     #
    # ------------------------------------------------------------------ #

    def _generate(self, messages: list, temperature: float = 0.7,
                  max_tokens: int = 256) -> str:
        self._ensure_client()

        if self.provider == "openai":
            resp = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()

        elif self.provider == "gemini":
            from google.genai import types
            system_msg = next(
                (m["content"] for m in messages if m["role"] == "system"), None
            )
            contents = [
                types.Content(
                    role="user" if m["role"] == "user" else "model",
                    parts=[types.Part(text=m["content"])],
                )
                for m in messages if m["role"] != "system"
            ]
            config = types.GenerateContentConfig(
                system_instruction=system_msg,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            resp = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )
            return resp.text.strip()

    # ------------------------------------------------------------------ #
    #  State detection — heuristic first, LLM fallback                   #
    # ------------------------------------------------------------------ #

    def _heuristic_state(self) -> dict:
        """Fast keyword-based state detection. Returns confidence flag."""
        user_msgs = [
            m["content"].lower()
            for m in self.history
            if m["role"] == "user" and not m["content"].startswith("[")
        ]
        recent_text = _normalize_text(" ".join(user_msgs[-3:]))
        all_text    = _normalize_text(" ".join(user_msgs))

        resistant_sigs  = [_normalize_text(s) for s in _RESISTANT_SIGNALS]
        expressive_sigs = [_normalize_text(s) for s in _EXPRESSIVE_SIGNALS]
        ready_sigs      = [_normalize_text(s) for s in _READY_SIGNALS]

        resistant_hits  = sum(1 for s in resistant_sigs  if s in recent_text)
        expressive_hits = sum(1 for s in expressive_sigs if s in all_text)
        ready_hits      = sum(1 for s in ready_sigs      if s in all_text)

        has_emotion  = any(s in all_text for s in _EMOTION_SIGNALS)
        has_scene    = any(s in all_text for s in _SCENE_SIGNALS)
        device_known = any(s in all_text for s in _DEVICE_SIGNALS)
        has_context  = len(user_msgs) >= 3 and any(
            len(m.split()) > 8 for m in user_msgs
        )

        if resistant_hits >= HEURISTIC_CONFIDENT_THRESHOLD:
            state, confident = "resistant", True
        elif ready_hits >= 1 and (has_emotion or has_scene):
            state, confident = "ready_to_create", True
        elif expressive_hits >= HEURISTIC_CONFIDENT_THRESHOLD or (has_emotion and has_scene):
            state, confident = "expressive", True
        else:
            state, confident = "exploring", False

        return {
            "state":       state,
            "has_emotion": has_emotion,
            "has_scene":   has_scene,
            "has_context": has_context,
            "device_known": device_known,
            "confident":   confident,
        }

    def _llm_state(self) -> dict:
        """LLM-based state assessment — called only when heuristic is inconclusive."""
        user_msgs = [
            m["content"]
            for m in self.history
            if m["role"] == "user" and not m["content"].startswith("[")
        ]
        recent   = "\n".join(user_msgs[-3:])
        convo    = "\n".join(f"User: {m}" for m in user_msgs)
        prompt   = STATE_ASSESSMENT_PROMPT.format(recent=recent, conversation=convo)
        response = self._generate(
            [{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=120,
        )
        try:
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
        return {}

    def _assess_state(self) -> dict:
        result = self._heuristic_state()
        # Only call LLM if heuristic is not confident, after turn 4
        if not result["confident"] and self.user_turn_count >= 4:
            try:
                llm = self._llm_state()
                if llm.get("state"):
                    result["state"] = llm["state"]
                    # merge specific flags from LLM if missing from heuristic
                    for key in ("has_emotion", "has_scene", "has_context", "device_known"):
                        if key in llm:
                            result[key] = result[key] or llm[key]
            except Exception:
                pass
        return result

    # ------------------------------------------------------------------ #
    #  Transition logic                                                   #
    # ------------------------------------------------------------------ #

    def _transition_signal(self, state_data: dict) -> str | None:
        """
        Returns 'full', 'soft', or None.
        full  → expressive/ready + (emotion OR scene) AND context
        soft  → resistant + (emotion OR scene)
        Never fires twice.
        """
        if self._transition_done:
            return None

        state       = state_data["state"]
        has_emotion = state_data["has_emotion"]
        has_scene   = state_data["has_scene"]
        has_context = state_data["has_context"]

        if state == "resistant" and self.user_turn_count >= 3:
            self._transition_done = True
            return "soft"

        if state in ("expressive", "ready_to_create"):
            if (has_emotion or has_scene) and has_context:
                self._transition_done = True
                return "full"

        return None

    # ------------------------------------------------------------------ #
    #  Coverage gate (state-aware)                                        #
    # ------------------------------------------------------------------ #

    def _coverage_met(self, state_data: dict) -> bool:
        state       = state_data["state"]
        has_core    = state_data["has_emotion"] or state_data["has_scene"]
        device_known = state_data["device_known"]

        # Hard stop
        if self.user_turn_count >= HARD_STOP_TURN:
            return True

        if not has_core:
            return False

        if self.user_turn_count < MIN_TURNS_BEFORE_CHECK:
            return False

        # Resistant users: must let stuck → re-entry flow play out first
        if state == "resistant":
            return self._stuck_fired

        # For expressive / ready / exploring, prefer device known
        return device_known or self.user_turn_count >= HARD_STOP_TURN - 1

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_minimal_response(text: str) -> bool:
        """True if the user's message is short or dismissive.
        Resistant signals take priority — a long dismissive sentence still counts.
        """
        text  = _normalize_text(text.strip().lower())
        words = text.split()
        norm_sigs = [_normalize_text(s) for s in _RESISTANT_SIGNALS]
        resistant_hits = sum(1 for s in norm_sigs if s in text)
        # Short regardless of signals
        if len(words) <= 5:
            return True
        # Moderate length + any resistant signal
        if len(words) <= 20 and resistant_hits >= 1:
            return True
        # Any length with strong resistant signal count
        if resistant_hits >= 2:
            return True
        return False

    @staticmethod
    def _is_reentry_signal(text: str) -> bool:
        """True if the user shows genuine small engagement — enough to re-enter.
        Requires actual scene/emotion content AND no dominant resistant signals.
        """
        text  = _normalize_text(text.strip().lower())
        words = text.split()
        if len(words) <= 3:
            return False
        has_scene      = any(s in text for s in _SCENE_SIGNALS)
        has_emotion    = any(s in text for s in _EMOTION_SIGNALS)
        norm_sigs      = [_normalize_text(s) for s in _RESISTANT_SIGNALS]
        resistant_hits = sum(1 for s in norm_sigs if s in text)
        # Must have scene or emotion content, and not dominated by resistant signals
        return (has_scene or has_emotion) and resistant_hits == 0

    @staticmethod
    def _extract_name(raw: str) -> str:
        raw = raw.strip().rstrip(".,!")
        for pattern in [
            r"(?:you can call me|call me|my name is|i(?:'m| am))\s+([A-Za-z]+)",
        ]:
            m = re.search(pattern, raw, re.IGNORECASE)
            if m:
                return m.group(1).capitalize()
        words = raw.split()
        if len(words) <= 2:
            return raw.capitalize()
        for word in words:
            if word and word[0].isupper():
                return word.rstrip(".,!")
        return raw.capitalize()

    _ALL_STYLES = [
        "Warm & Film", "Clean & Bright", "Moody & Dark",
        "Documentary", "Soft & Dreamy", "Gritty & Urban",
    ]

    def _select_styles(self) -> list:
        """LLM picks 2-3 styles relevant to this user's expressed intent.
        Falls back to all styles if the call fails or returns invalid names."""
        transcript = self._format_transcript(self.history)
        prompt     = STYLE_SELECTION_PROMPT.format(conversation=transcript)
        try:
            response = self._generate(
                [{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=60,
            )
            match = re.search(r"\[.*?\]", response, re.DOTALL)
            if match:
                chosen = json.loads(match.group())
                valid  = [s for s in chosen if s in self._ALL_STYLES]
                if len(valid) >= 2:
                    return valid[:3]
        except Exception:
            pass
        return list(self._ALL_STYLES)   # fallback: show everything

    def _should_show_style_grid(self, agent_reply: str) -> bool:
        if self.style_grid_shown:
            return False
        if self.user_turn_count < 4:
            return False
        reply_lower = agent_reply.lower()
        keywords = [
            "style", "mood", "tone", "atmosphere", "aesthetic", "visual",
            "warm", "dark", "bright", "colour", "color", "film", "soft",
            "gritty", "moody", "image", "photo",
        ]
        keyword_hit = any(kw in reply_lower for kw in keywords)
        fallback    = self.user_turn_count >= 7
        return keyword_hit or fallback

    @staticmethod
    def _format_transcript(messages: list) -> str:
        parts = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            if msg["content"].startswith("["):  # filter all system notes
                continue
            role = "User" if msg["role"] == "user" else "Agent"
            parts.append(f"{role}: {msg['content']}")
        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    #  Profile extraction                                                 #
    # ------------------------------------------------------------------ #

    def _extract_profile(self, conversation: str) -> dict:
        prompt   = EXTRACTION_PROMPT.format(conversation=conversation)
        response = self._generate(
            [{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=500,
        )
        try:
            cleaned = re.sub(r"```(?:json)?", "", response).strip()
            match   = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
        return {}

    # ------------------------------------------------------------------ #
    #  Stateful API — used by Gradio frontend                            #
    # ------------------------------------------------------------------ #

    def start(self) -> str:
        self.history          = [{"role": "system", "content": INTERVIEW_SYSTEM}]
        self.user_turn_count  = 0
        self.style_grid_shown = False
        self.style_selection  = []   # populated when grid triggers
        self.is_done          = False
        self._awaiting_name   = False
        self._name_collected  = None
        self._user_state        = "exploring"
        self._transition_done   = False
        self._post_soft_turns   = 0     # turns since soft transition fired
        self._stuck_fired       = False # stuck signal sent once
        self._waiting_reentry   = False # passive wait after stuck exercise
        self._reentry_wait_count = 0   # how many turns spent waiting for re-entry

        opening = random.choice(OPENING_MESSAGES)
        self.history.append({"role": "assistant", "content": opening})
        return opening

    def chat(self, user_message: str) -> tuple:
        """
        Returns (reply: str, show_style_grid: bool, is_done: bool)
        """
        # ── Phase 2: collecting name ────────────────────────────────────
        if self._awaiting_name:
            self._name_collected = self._extract_name(user_message)
            self.history.append({"role": "user", "content": user_message})
            closing = (
                f"Lovely to meet you, {self._name_collected}. "
                "I've got a good sense of what you're after — "
                "let's get started whenever you're ready."
            )
            self.history.append({"role": "assistant", "content": closing})
            self.is_done = True
            return closing, False, True

        # ── Normal turn ─────────────────────────────────────────────────
        self.history.append({"role": "user", "content": user_message})
        self.user_turn_count += 1

        # State assessment
        state_data = (
            self._assess_state()
            if self.user_turn_count >= 2
            else {
                "state": "exploring", "has_emotion": False, "has_scene": False,
                "has_context": False, "device_known": False, "confident": False,
            }
        )
        self._user_state = state_data["state"]

        # ── Stuck / re-entry tracking (post soft-transition) ───────────
        if self._transition_done and state_data["state"] == "resistant":
            self._post_soft_turns += 1

        if self._waiting_reentry:
            self._reentry_wait_count += 1
            if self._is_reentry_signal(user_message):
                # Genuine re-engagement — trigger teaching mode
                self._waiting_reentry = False
                self._user_state = "re_entry"
                self.history.append({"role": "user", "content": RE_ENTRY_SIGNAL})
            elif self._reentry_wait_count >= 3:
                # Waited 3 turns, user still not engaging — close window gracefully
                self._waiting_reentry = False
        elif (
            self._transition_done
            and not self._stuck_fired
            and self._post_soft_turns >= 2
            and self._is_minimal_response(user_message)
        ):
            self._stuck_fired     = True
            self._waiting_reentry = True
            self._user_state      = "stuck"
            self.history.append({"role": "user", "content": STUCK_SIGNAL})

        # Inject state hint — skip during passive wait (agent already has exercise instructions)
        elif self.user_turn_count >= 2:
            hint_state = self._user_state if self._user_state in STATE_STRATEGIES else "exploring"
            self.history.append({
                "role": "user",
                "content": (
                    f"[system_note: user_state={hint_state}. "
                    f"{STATE_STRATEGIES[hint_state]}]"
                ),
            })

        # Transition signal (fires at most once, not for resistant)
        t = self._transition_signal(state_data)
        if t == "full":
            self.history.append({"role": "user", "content": FULL_TRANSITION_SIGNAL})
        elif t == "soft":
            self.history.append({"role": "user", "content": SOFT_TRANSITION_SIGNAL})

        # Coverage check (state-aware, periodic)
        if (
            self.user_turn_count >= MIN_TURNS_BEFORE_CHECK
            and self.user_turn_count % COVERAGE_CHECK_EVERY == 0
            or self.user_turn_count >= HARD_STOP_TURN
        ):
            if self._coverage_met(state_data):
                self.history.append({"role": "user", "content": WRAP_UP_SIGNAL})
                reply     = self._generate(self.history, temperature=0.7, max_tokens=120)
                full_reply = reply.rstrip() + f"\n\n{NAME_QUESTION}"
                self.history.append({"role": "assistant", "content": full_reply})
                self._awaiting_name = True
                return full_reply, False, False

        # Generate reply
        reply = self._generate(self.history, temperature=0.75, max_tokens=180)
        self.history.append({"role": "assistant", "content": reply})

        # Style grid — contextual trigger
        show_grid = self._should_show_style_grid(reply)
        if show_grid:
            self.style_grid_shown = True
            self.style_selection  = self._select_styles()

        return reply, show_grid, False

    def inject_style(self, style_names: list) -> str:
        """Feed style selection into history without incrementing user_turn_count."""
        if style_names and style_names != ["no particular style yet"]:
            note = (
                f"[system_note: user selected visual styles: {', '.join(style_names)}. "
                f"Acknowledge briefly in one sentence and continue naturally.]"
            )
        else:
            note = (
                "[system_note: user was shown style examples but skipped. "
                "Acknowledge briefly and continue naturally.]"
            )
        self.history.append({"role": "user", "content": note})
        reply = self._generate(self.history, temperature=0.7, max_tokens=100)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def finalize(self) -> UserProfile:
        transcript = self._format_transcript(self.history)
        extracted  = self._extract_profile(transcript)
        name       = self._name_collected or extracted.get("name", "Anonymous")
        profile    = UserProfile(
            name               = name,
            photographic_intent= extracted.get("photographic_intent", ""),
            subject_world      = extracted.get("subject_world", ""),
            teaching_direction = extracted.get("teaching_direction", ""),
            device             = extracted.get("device", "unknown"),
            visual_references  = extracted.get("visual_references", ""),
            inferred_level     = int(extracted.get("inferred_level", 1)),
            skill_model        = SkillModel(),
            performance_history= [],
        )
        profile.save(self.profile_dir)
        return profile

    # ------------------------------------------------------------------ #
    #  CLI loop                                                           #
    # ------------------------------------------------------------------ #

    def run(self) -> UserProfile:
        print("\n" + "=" * 52)
        print("  Photography Profile Interview")
        print("=" * 52 + "\n")

        opening = self.start()
        print(f"Agent: {opening}\n")

        while self.user_turn_count < MAX_TURNS:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            reply, show_grid, done = self.chat(user_input)

            if show_grid:
                print("\n[Style grid would appear here in the UI]\n")

            print(f"\nAgent: {reply}\n")

            if done:
                break

        print("Building your profile...\n")
        profile = self.finalize()
        print("=" * 52)
        print(profile.to_teacher_context())
        slug = profile.name.lower().replace(" ", "_")
        print(f"\nSaved → profiles/{slug}.json\n")
        return profile


# ------------------------------------------------------------------ #
#  Entry point                                                        #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="openai", choices=["openai", "gemini"])
    args = parser.parse_args()
    InterviewAgent(provider=args.provider).run()
