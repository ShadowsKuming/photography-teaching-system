"""
Photography Teaching System — Unified App
Run:  python app.py

Flow:
  Landing → New student  → Interview → Teaching
          → Return student (pick profile) → Teaching
"""

import os
import glob

import gradio as gr
from PIL import Image, ImageDraw, ImageFilter

from interview.agent import InterviewAgent
from interview.profile import UserProfile
from teaching.teacher import TeacherAgent


PROFILE_DIR = "profiles"

# ------------------------------------------------------------------ #
#  Style definitions + placeholder images                             #
# ------------------------------------------------------------------ #

STYLES = [
    {"name": "Warm & Film",     "description": "Faded, golden — feels like a memory",      "colors": [(210, 140, 60),  (240, 190, 100)]},
    {"name": "Clean & Bright",  "description": "Sharp, airy, magazine-like",                "colors": [(180, 215, 240), (240, 248, 255)]},
    {"name": "Moody & Dark",    "description": "High contrast, dramatic shadows",           "colors": [(20, 20, 50),    (70, 50, 90)]},
    {"name": "Documentary",     "description": "Raw, unposed, in-the-moment",               "colors": [(90, 90, 90),    (160, 155, 145)]},
    {"name": "Soft & Dreamy",   "description": "Gentle light, blurred backgrounds",         "colors": [(220, 185, 210), (245, 225, 235)]},
    {"name": "Gritty & Urban",  "description": "Harsh light, real textures",                "colors": [(50, 50, 50),    (110, 100, 85)]},
]


def _make_placeholder(colors, size=(300, 180)):
    w, h = size
    img  = Image.new("RGB", size)
    c1, c2 = colors
    for y in range(h):
        t = y / h
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    return img.filter(ImageFilter.GaussianBlur(radius=2))


STYLE_IMAGES = [_make_placeholder(s["colors"]) for s in STYLES]


# ------------------------------------------------------------------ #
#  Profile helpers                                                    #
# ------------------------------------------------------------------ #

def _list_profiles():
    paths = glob.glob(os.path.join(PROFILE_DIR, "*.json"))
    names = [os.path.splitext(os.path.basename(p))[0] for p in sorted(paths)]
    return names


def _load_profile(name):
    try:
        return UserProfile.load(name, PROFILE_DIR)
    except Exception:
        return None


def _profile_summary(profile):
    lines = [
        f"**{profile.name}**",
        f"Intent: {profile.photographic_intent or '—'}",
        f"Device: {profile.device or '—'}  |  Level: {profile.inferred_level}/5",
        f"Sessions completed: {len(profile.performance_history)}",
    ]
    return "\n\n".join(lines)


# ------------------------------------------------------------------ #
#  App                                                                #
# ------------------------------------------------------------------ #

def create_app():
    with gr.Blocks(title="Photography Teaching") as demo:

        # ── shared state ──
        interview_agent_state = gr.State(None)
        teacher_agent_state   = gr.State(None)
        profile_state         = gr.State(None)
        grid_visible          = gr.State(False)
        selected_styles       = gr.State([])

        # ================================================================
        # PANEL 1 — LANDING
        # ================================================================
        with gr.Column(visible=True) as landing_panel:
            gr.Markdown("# Photography Teaching System")
            gr.Markdown("Learn photography through personalised one-on-one teaching.")

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### New student")
                    gr.Markdown("Start with a short interview so we can understand your photographic vision.")
                    new_btn = gr.Button("Start interview", variant="primary", size="lg")

                with gr.Column(scale=1):
                    gr.Markdown("### Returning student")
                    gr.Markdown("Pick up where you left off.")
                    profile_names = _list_profiles()
                    profile_dropdown = gr.Dropdown(
                        label="Select your profile",
                        choices=profile_names if profile_names else ["(no profiles yet)"],
                        value=None,
                        interactive=bool(profile_names),
                    )
                    return_btn = gr.Button(
                        "Continue lesson",
                        variant="secondary",
                        size="lg",
                        interactive=False,
                    )

        # ================================================================
        # PANEL 2 — INTERVIEW
        # ================================================================
        with gr.Column(visible=False) as interview_panel:
            gr.Markdown("## Getting to know you")
            gr.Markdown(
                "Have a conversation with our assistant. "
                "It will understand your vision and build your learner profile."
            )

            interview_chatbot = gr.Chatbot(label="", height=400)

            with gr.Column(visible=False) as style_panel:
                gr.Markdown("### What visual style feels closest to you?")
                gr.Markdown("*Select one or two that resonate — doesn't have to be exact.*")

                with gr.Row():
                    style_checks = []
                    style_cols   = []
                    for i, style in enumerate(STYLES):
                        with gr.Column(scale=1, min_width=160, visible=True) as col:
                            gr.Image(
                                value=STYLE_IMAGES[i],
                                label=style["name"],
                                show_label=True,
                                interactive=False,
                                height=140,
                            )
                            cb = gr.Checkbox(label=style["description"], value=False)
                            style_checks.append(cb)
                        style_cols.append(col)

                confirm_btn = gr.Button("Confirm my style picks", variant="primary")

            with gr.Row():
                interview_input = gr.Textbox(
                    placeholder="Type your message here...",
                    show_label=False,
                    scale=5,
                    container=False,
                )
                interview_send = gr.Button("Send", variant="primary", scale=1)

        # ================================================================
        # PANEL 3 — TEACHING
        # ================================================================
        with gr.Column(visible=False) as teaching_panel:

            with gr.Row():
                with gr.Column(scale=3):
                    teach_chatbot = gr.Chatbot(label="", height=500)

                    with gr.Column(visible=False) as upload_panel:
                        gr.Markdown("*Upload a photo when you're ready.*")
                        photo_upload = gr.Image(
                            label="Your photo",
                            type="pil",
                            height=240,
                        )

                    with gr.Row():
                        teach_input = gr.Textbox(
                            placeholder="Type your message...",
                            show_label=False,
                            scale=5,
                            container=False,
                        )
                        teach_send = gr.Button("Send", variant="primary", scale=1)

                with gr.Column(scale=1, min_width=200):
                    gr.Markdown("### Student")
                    student_info = gr.Markdown("")
                    gr.Markdown("---")
                    gr.Markdown("### Phase")
                    phase_box = gr.Textbox(label="", interactive=False, lines=1)

        # ================================================================
        # HANDLERS — LANDING
        # ================================================================

        def on_new_student():
            agent   = InterviewAgent(provider="openai", profile_dir=PROFILE_DIR)
            opening = agent.start()
            history = [{"role": "assistant", "content": opening}]
            return (
                gr.update(visible=False),   # landing_panel
                gr.update(visible=True),    # interview_panel
                gr.update(visible=False),   # teaching_panel
                history,                    # interview_chatbot
                agent,                      # interview_agent_state
            )

        def on_profile_select(name):
            if not name or name == "(no profiles yet)":
                return gr.update(interactive=False), None
            profile = _load_profile(name)
            if profile is None:
                return gr.update(interactive=False), None
            return gr.update(interactive=True), profile

        def on_return_student(profile):
            if profile is None:
                return (gr.update(),) * 7 + (None, "")
            agent  = TeacherAgent(profile=profile, provider="openai",
                                  eval_provider="openai", profile_dir=PROFILE_DIR)
            result = agent.start()
            history = [{"role": "assistant", "content": result.reply}]
            return (
                gr.update(visible=False),              # landing_panel
                gr.update(visible=False),              # interview_panel
                gr.update(visible=True),               # teaching_panel
                history,                               # teach_chatbot
                gr.update(visible=result.show_upload), # upload_panel
                result.phase.value,                    # phase_box
                _profile_summary(profile),             # student_info
                agent,                                 # teacher_agent_state
                profile.name,                          # title marker (unused, just gr.Markdown update)
            )

        # ================================================================
        # HANDLERS — INTERVIEW
        # ================================================================

        def on_interview_send(user_msg, history, agent, gv):
            if not user_msg.strip() or agent is None:
                return (
                    history, "",
                    gr.update(), agent, gv,
                ) + tuple([gr.update()] * len(STYLES))

            history = history + [{"role": "user", "content": user_msg}]
            reply, show_grid, is_done = agent.chat(user_msg)
            history = history + [{"role": "assistant", "content": reply}]

            if show_grid:
                gv = True
            grid_update = gr.update(visible=gv)

            if show_grid:
                chosen = agent.style_selection or [s["name"] for s in STYLES]
                col_updates = tuple(gr.update(visible=(s["name"] in chosen)) for s in STYLES)
            else:
                col_updates = tuple(gr.update() for _ in STYLES)

            if is_done:
                # Transition to teaching
                profile = agent.finalize()
                t_agent = TeacherAgent(profile=profile, provider="openai",
                                       eval_provider="openai", profile_dir=PROFILE_DIR)
                t_result = t_agent.start()
                t_history = [{"role": "assistant", "content": t_result.reply}]
                # Return teaching panel + clear interview state
                return (
                    history, "",
                    gr.update(visible=False),  # style_panel
                    agent, False,
                ) + (gr.update(),) * len(STYLES) + (
                    gr.update(visible=False),   # interview_panel
                    gr.update(visible=True),    # teaching_panel
                    t_history,                  # teach_chatbot
                    gr.update(visible=t_result.show_upload),  # upload_panel
                    t_result.phase.value,       # phase_box
                    _profile_summary(profile),  # student_info
                    t_agent,                    # teacher_agent_state
                )

            return (
                history, "",
                grid_update,
                agent, gv,
            ) + col_updates + (
                gr.update(),   # interview_panel
                gr.update(),   # teaching_panel
                gr.update(),   # teach_chatbot
                gr.update(),   # upload_panel
                gr.update(),   # phase_box
                gr.update(),   # student_info
                gr.update(),   # teacher_agent_state
            )

        def on_confirm_style(*args):
            *checkbox_values, history, agent = args
            chosen = [STYLES[i]["name"] for i, v in enumerate(checkbox_values) if v]
            if not chosen:
                chosen = ["no particular style yet"]
            reply   = agent.inject_style(chosen)
            history = history + [
                {"role": "user",      "content": f"*(selected styles: {', '.join(chosen)})*"},
                {"role": "assistant", "content": reply},
            ]
            reset_checks = [gr.update(value=False)] * len(STYLES)
            reset_cols   = [gr.update(visible=True)] * len(STYLES)
            return [history, gr.update(visible=False), agent, False] + reset_checks + reset_cols

        # ================================================================
        # HANDLERS — TEACHING
        # ================================================================

        def on_teach_send(user_msg, photo, history, agent):
            if agent is None:
                return history, "", None, gr.update(), gr.update(), agent

            msg   = (user_msg or "").strip()
            image = photo  # PIL or None

            if not msg and image is None:
                return history, "", None, gr.update(), gr.update(), agent

            display_msg = msg if msg else "*(photo submitted)*"
            history = history + [{"role": "user", "content": display_msg}]

            result  = agent.chat(msg, image)
            history = history + [{"role": "assistant", "content": result.reply}]

            return (
                history,
                "",                                     # clear text
                None,                                   # clear photo
                result.phase.value,                     # phase_box
                gr.update(visible=result.show_upload),  # upload_panel
                agent,
            )

        # ================================================================
        # WIRE UP EVENTS
        # ================================================================

        # Landing
        new_btn.click(
            on_new_student,
            outputs=[landing_panel, interview_panel, teaching_panel,
                     interview_chatbot, interview_agent_state],
        )

        profile_dropdown.change(
            on_profile_select,
            inputs=[profile_dropdown],
            outputs=[return_btn, profile_state],
        )

        return_btn.click(
            on_return_student,
            inputs=[profile_state],
            outputs=[landing_panel, interview_panel, teaching_panel,
                     teach_chatbot, upload_panel, phase_box, student_info,
                     teacher_agent_state, student_info],
        )

        # Interview
        interview_send_outputs = [
            interview_chatbot, interview_input,
            style_panel,
            interview_agent_state, grid_visible,
        ] + style_cols + [
            interview_panel, teaching_panel,
            teach_chatbot, upload_panel, phase_box, student_info,
            teacher_agent_state,
        ]

        interview_send.click(
            on_interview_send,
            inputs=[interview_input, interview_chatbot, interview_agent_state, grid_visible],
            outputs=interview_send_outputs,
        )
        interview_input.submit(
            on_interview_send,
            inputs=[interview_input, interview_chatbot, interview_agent_state, grid_visible],
            outputs=interview_send_outputs,
        )

        confirm_btn.click(
            on_confirm_style,
            inputs=style_checks + [interview_chatbot, interview_agent_state],
            outputs=[interview_chatbot, style_panel, interview_agent_state, grid_visible]
                    + style_checks + style_cols,
        )

        # Teaching
        teach_send_outputs = [
            teach_chatbot, teach_input, photo_upload,
            phase_box, upload_panel, teacher_agent_state,
        ]

        teach_send.click(
            on_teach_send,
            inputs=[teach_input, photo_upload, teach_chatbot, teacher_agent_state],
            outputs=teach_send_outputs,
        )
        teach_input.submit(
            on_teach_send,
            inputs=[teach_input, photo_upload, teach_chatbot, teacher_agent_state],
            outputs=teach_send_outputs,
        )

    return demo


if __name__ == "__main__":
    app = create_app()
    app.launch(
        share=False,
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", 7860)),
        theme=gr.themes.Soft(),
    )
