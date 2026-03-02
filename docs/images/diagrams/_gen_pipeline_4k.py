#!/usr/bin/env python3
"""Generate a 4K GCP-branded Multi-Agent Pipeline Architecture diagram.

All agent names, model names, and hierarchy verified against:
  - trends_and_insights_agent/shared_libraries/config.py
  - trends_and_insights_agent/agent.py
  - Each skill's agents.py
"""

from PIL import Image, ImageDraw, ImageFont
import math

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H = 3840, 2160
BG = "#FFFFFF"

# ── GCP Brand Colors ─────────────────────────────────────────────────────────
BLUE       = "#4285F4"
YELLOW     = "#FBBC04"
GREEN      = "#34A853"
RED        = "#EA4335"
PURPLE     = "#A142F4"
TEAL       = "#12B5CB"
DARK_GRAY  = "#3C4043"
MED_GRAY   = "#5F6368"
LIGHT_GRAY = "#E8EAED"
VERY_LIGHT = "#F8F9FA"
WHITE      = "#FFFFFF"
ORANGE     = "#F4A828"

# ── Fonts ─────────────────────────────────────────────────────────────────────
def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def font_bold(sz):
    return _font("/usr/share/fonts/truetype/roboto/unhinted/RobotoCondensed-Bold.ttf", sz)

def font_medium(sz):
    return _font("/usr/share/fonts/truetype/roboto/unhinted/RobotoCondensed-Medium.ttf", sz)

def font_regular(sz):
    return _font("/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Regular.ttf", sz)

def font_light(sz):
    return _font("/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Light.ttf", sz)

# Font sizes scaled for 4K
F_TITLE     = font_bold(56)
F_SUBTITLE  = font_light(32)
F_SKILL_HDR = font_bold(30)
F_AGENT_LG  = font_bold(26)
F_AGENT_MD  = font_bold(22)
F_AGENT_SM  = font_bold(18)
F_BODY      = font_regular(18)
F_BODY_SM   = font_regular(16)
F_LABEL     = font_bold(19)
F_MODEL     = font_regular(18)
F_LEGEND    = font_regular(20)
F_LEGEND_T  = font_bold(22)
F_FOOTER    = font_regular(18)

# ── Color helpers ─────────────────────────────────────────────────────────────
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lighten(c, f=0.85):
    r, g, b = hex_rgb(c)
    return "#{:02x}{:02x}{:02x}".format(int(r+(255-r)*f), int(g+(255-g)*f), int(b+(255-b)*f))

def darken(c, f=0.3):
    r, g, b = hex_rgb(c)
    return "#{:02x}{:02x}{:02x}".format(int(r*(1-f)), int(g*(1-f)), int(b*(1-f)))

# ── Drawing helpers ───────────────────────────────────────────────────────────
def tw(draw, text, fnt):
    bb = draw.textbbox((0,0), text, font=fnt)
    return bb[2] - bb[0]

def th(draw, text, fnt):
    bb = draw.textbbox((0,0), text, font=fnt)
    return bb[3] - bb[1]

def rrect(draw, box, r, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = box
    r = min(r, (x1-x0)//2, (y1-y0)//2)
    if fill:
        draw.rectangle([x0+r, y0, x1-r, y1], fill=fill)
        draw.rectangle([x0, y0+r, x1, y1-r], fill=fill)
        draw.pieslice([x0, y0, x0+2*r, y0+2*r], 180, 270, fill=fill)
        draw.pieslice([x1-2*r, y0, x1, y0+2*r], 270, 360, fill=fill)
        draw.pieslice([x0, y1-2*r, x0+2*r, y1], 90, 180, fill=fill)
        draw.pieslice([x1-2*r, y1-2*r, x1, y1], 0, 90, fill=fill)
    if outline:
        draw.arc([x0, y0, x0+2*r, y0+2*r], 180, 270, fill=outline, width=width)
        draw.arc([x1-2*r, y0, x1, y0+2*r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1-2*r, x0+2*r, y1], 90, 180, fill=outline, width=width)
        draw.arc([x1-2*r, y1-2*r, x1, y1], 0, 90, fill=outline, width=width)
        draw.line([x0+r, y0, x1-r, y0], fill=outline, width=width)
        draw.line([x0+r, y1, x1-r, y1], fill=outline, width=width)
        draw.line([x0, y0+r, x0, y1-r], fill=outline, width=width)
        draw.line([x1, y0+r, x1, y1-r], fill=outline, width=width)

def arrow(draw, x1, y1, x2, y2, color=MED_GRAY, w=3, hs=10):
    draw.line([x1,y1,x2,y2], fill=color, width=w)
    a = math.atan2(y2-y1, x2-x1)
    pts = [
        (x2, y2),
        (x2 - hs*math.cos(a-math.pi/6), y2 - hs*math.sin(a-math.pi/6)),
        (x2 - hs*math.cos(a+math.pi/6), y2 - hs*math.sin(a+math.pi/6)),
    ]
    draw.polygon(pts, fill=color)

def small_arrow_down(draw, cx, y1, y2, color=MED_GRAY):
    draw.line([cx, y1, cx, y2], fill=color, width=2)
    draw.polygon([(cx, y2), (cx-4, y2-6), (cx+4, y2-6)], fill=color)

def agent_box(draw, x, y, w, h, name, sub=None, color=BLUE, fnm=None, fsub=None):
    fnm = fnm or F_AGENT_SM
    fsub = fsub or F_BODY_SM
    fill = lighten(color, 0.88)
    rrect(draw, (x, y, x+w, y+h), 10, fill=fill, outline=color, width=2)
    draw.rectangle([x+10, y, x+w-10, y+5], fill=color)
    ntw = tw(draw, name, fnm)
    draw.text((x + (w-ntw)//2, y+8), name, fill=darken(color, 0.2), font=fnm)
    if sub:
        stw = tw(draw, sub, fsub)
        draw.text((x + (w-stw)//2, y + 8 + th(draw, name, fnm) + 3), sub, fill=MED_GRAY, font=fsub)

def tool_box(draw, x, y, w, h, name, fnm=None):
    fnm = fnm or F_BODY_SM
    rrect(draw, (x, y, x+w, y+h), 6, fill=LIGHT_GRAY, outline=MED_GRAY, width=1)
    ntw = tw(draw, name, fnm)
    draw.text((x + (w-ntw)//2, y + (h - th(draw, name, fnm))//2), name, fill=DARK_GRAY, font=fnm)

def section_box(draw, x, y, w, h, title, sub=None, color=GREEN, fnm=None, fsub=None):
    """A labeled sub-section (pipeline / composition) box."""
    fnm = fnm or F_BODY_SM
    fsub = fsub or F_BODY_SM
    rrect(draw, (x, y, x+w, y+h), 8, fill=lighten(color, 0.95), outline=color, width=2)
    draw.text((x+8, y+5), title, fill=darken(color, 0.15), font=fnm)
    if sub:
        draw.text((x+8, y+5 + th(draw, title, fnm)+2), sub, fill=color, font=fsub)

def inner_agent(draw, x, y, w, h, name, color=GREEN, fnm=None):
    fnm = fnm or F_BODY_SM
    rrect(draw, (x, y, x+w, y+h), 5, fill=lighten(color, 0.88), outline=color, width=1)
    draw.text((x+6, y + (h - th(draw, name, fnm))//2), name, fill=darken(color, 0.2), font=fnm)


# ══════════════════════════════════════════════════════════════════════════════
# CREATE IMAGE
# ══════════════════════════════════════════════════════════════════════════════
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# ── Title ─────────────────────────────────────────────────────────────────────
d.rectangle([0, 0, W, 90], fill=BLUE)
title_text = "Marketing Intelligence  --  Multi-Agent Pipeline Architecture"
ttw = tw(d, title_text, F_TITLE)
d.text(((W-ttw)//2, 16), title_text, fill=WHITE, font=F_TITLE)

sub_text = "Skills-Based Agent Hierarchy with ADK  |  v1.0 -- March 2026"
stw2 = tw(d, sub_text, F_SUBTITLE)
d.text(((W-stw2)//2, 96), sub_text, fill=MED_GRAY, font=F_SUBTITLE)

# ── Root Agent ────────────────────────────────────────────────────────────────
rx, ry, rw, rh = (W-540)//2, 142, 540, 72
rrect(d, (rx, ry, rx+rw, ry+rh), 14, fill=lighten(BLUE, 0.75), outline=BLUE, width=4)
d.rectangle([rx+14, ry, rx+rw-14, ry+6], fill=BLUE)
rt = "root_agent  --  Orchestrator"
rtw_ = tw(d, rt, F_AGENT_LG)
d.text((rx+(rw-rtw_)//2, ry+12), rt, fill=BLUE, font=F_AGENT_LG)
mt = "gemini-2.5-flash  |  BuiltInPlanner (thinking)"
mtw_ = tw(d, mt, F_MODEL)
d.text((rx+(rw-mtw_)//2, ry+42), mt, fill=MED_GRAY, font=F_MODEL)

# ── Column layout ────────────────────────────────────────────────────────────
MX = 24          # margin
GAP = 14         # gap between columns
COL_W = (W - 2*MX - 4*GAP) // 5
COL_TOP = 268
COL_BOT = 1960

COLORS = [YELLOW, GREEN, RED, PURPLE, TEAL]
TITLES = [
    "Skill 1: Trend Discovery",
    "Skill 2: Market Research",
    "Skill 3: Ad Creative",
    "Skill 4: AV Studio",
    "Skill 5: Focus Group",
]

# Connector lines root -> columns
for i in range(5):
    cx = MX + i*(COL_W+GAP) + COL_W//2
    arrow(d, W//2, ry+rh, cx, COL_TOP+4, color=lighten(BLUE, 0.3), w=2, hs=8)

# Column backgrounds + headers
for i in range(5):
    cx = MX + i*(COL_W+GAP)
    rrect(d, (cx, COL_TOP, cx+COL_W, COL_BOT), 14,
          fill=VERY_LIGHT, outline=lighten(COLORS[i], 0.5), width=2)
    d.text((cx+14, COL_TOP+10), TITLES[i], fill=COLORS[i], font=F_SKILL_HDR)
    d.line([cx+14, COL_TOP+44, cx+COL_W-14, COL_TOP+44], fill=COLORS[i], width=3)


# ══════════════════════════════════════════════════════════════════════════════
# SKILL 1: TREND DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
c1x = MX
c1w = COL_W
y = COL_TOP + 55

agent_box(d, c1x+14, y, c1w-28, 55,
          "trends_and_insights_agent", "LLM Agent  |  gemini-2.5-flash", YELLOW, F_AGENT_MD)

y += 70
d.text((c1x+22, y), "Tools (6):", fill=DARK_GRAY, font=F_LABEL)
y += 26

tools_s1 = [
    "memorize",
    "get_daily_gtrends",
    "get_youtube_trends",
    "save_yt_trends_to_session_state",
    "save_search_trends_to_session_state",
    "auto_select_trends",
]
for t in tools_s1:
    tool_box(d, c1x+22, y, c1w-44, 32, t)
    y += 38

y += 20
d.text((c1x+22, y), "Writes to Session State:", fill=DARK_GRAY, font=F_LABEL)
y += 26
for sk in [
    "brand", "target_product",
    "target_audience", "key_selling_points",
    "target_search_trends", "target_yt_trends",
    "campaign_guide_content",
]:
    d.text((c1x+30, y), "- " + sk, fill=MED_GRAY, font=F_BODY_SM)
    y += 22

y += 20
d.text((c1x+22, y), "Data Sources:", fill=DARK_GRAY, font=F_LABEL)
y += 26
for ds in ["Google Trends API", "YouTube Data API v3", "User-uploaded PDF"]:
    rrect(d, (c1x+22, y, c1x+c1w-22, y+30), 6,
          fill=lighten(YELLOW, 0.92), outline=lighten(YELLOW, 0.4), width=1)
    d.text((c1x+30, y+6), ds, fill=darken(YELLOW, 0.25), font=F_BODY_SM)
    y += 36


# ══════════════════════════════════════════════════════════════════════════════
# SKILL 2: MARKET RESEARCH
# ══════════════════════════════════════════════════════════════════════════════
c2x = MX + (COL_W+GAP)
c2w = COL_W
y = COL_TOP + 55

agent_box(d, c2x+14, y, c2w-28, 55,
          "research_orchestrator", "LLM Agent  |  gemini-2.5-flash", GREEN, F_AGENT_MD)

y += 68
# combined_research_pipeline
crp_y = y
crp_h = 960
section_box(d, c2x+10, crp_y, c2w-20, crp_h,
            "combined_research_pipeline", "(AgentTool, Sequential)", GREEN)
y = crp_y + 38

# merge_parallel_insights
mpi_y = y
mpi_h = 590
section_box(d, c2x+16, mpi_y, c2w-32, mpi_h,
            "merge_parallel_insights", "(Sequential)", GREEN, F_BODY_SM)
y = mpi_y + 36

# parallel_planner_agent
pp_y = y
pp_h = 470
rrect(d, (c2x+22, pp_y, c2x+c2w-22, pp_y+pp_h), 8,
      fill=lighten(PURPLE, 0.94), outline=PURPLE, width=2)
d.text((c2x+30, pp_y+5), "parallel_planner_agent (Parallel)", fill=PURPLE, font=F_BODY_SM)

# 3 parallel lanes
lane_top = pp_y + 28
lane_gap = 6
lane_inner_w = c2w - 56
lane_w = (lane_inner_w - 2*lane_gap) // 3
lane_h = 430

lanes = [
    ("YT Research", [
        ("yt_sequential_planner", True),
        ("yt_analysis_gen_agent", False),
        ("  (video understanding)", None),
        ("yt_web_planner", False),
        ("yt_web_searcher", False),
    ]),
    ("GS Research", [
        ("gs_sequential_planner", True),
        ("gs_web_planner", False),
        ("gs_web_searcher", False),
    ]),
    ("CA Research", [
        ("ca_sequential_planner", True),
        ("campaign_web_planner", False),
        ("campaign_web_searcher", False),
    ]),
]

for li, (lane_title, agents) in enumerate(lanes):
    lx = c2x + 28 + li*(lane_w + lane_gap)
    rrect(d, (lx, lane_top, lx+lane_w, lane_top+lane_h), 6,
          fill=lighten(GREEN, 0.96), outline=lighten(GREEN, 0.4), width=1)
    d.text((lx+4, lane_top+4), lane_title, fill=darken(GREEN, 0.15), font=F_BODY_SM)
    ay = lane_top + 26
    prev_bottom = None
    for name, is_agent in agents:
        if is_agent is None:  # annotation
            d.text((lx+6, ay-2), name, fill=MED_GRAY, font=F_BODY_SM)
            ay += 18
            continue
        bh = 28
        if prev_bottom is not None:
            small_arrow_down(d, lx+lane_w//2, prev_bottom+2, ay-2, GREEN)
        inner_agent(d, lx+4, ay, lane_w-8, bh, name, GREEN)
        prev_bottom = ay + bh
        ay += bh + 10

# merge_planners
y = pp_y + pp_h + 8
inner_agent(d, c2x+22, y, c2w-44, 30, "merge_planners", GREEN)

# End of merge_parallel_insights is at mpi_y + mpi_h

# Post-parallel sequential steps
y = mpi_y + mpi_h + 10
post_steps = [
    ("combined_web_evaluator", "Critic  |  quality check"),
    ("enhanced_combined_searcher", "Follow-up web search"),
    ("combined_report_composer", "Final cited report"),
]
for pi, (pname, pdesc) in enumerate(post_steps):
    rrect(d, (c2x+16, y, c2x+c2w-16, y+48), 6,
          fill=lighten(GREEN, 0.88), outline=GREEN, width=1)
    d.text((c2x+24, y+4), pname, fill=darken(GREEN, 0.2), font=F_BODY_SM)
    d.text((c2x+24, y+24), pdesc, fill=MED_GRAY, font=F_BODY_SM)
    y += 56
    if pi < len(post_steps)-1:
        small_arrow_down(d, c2x+c2w//2, y-10, y-2, GREEN)

# Extra tools below pipeline
y = crp_y + crp_h + 16
d.text((c2x+22, y), "Orchestrator Tools:", fill=DARK_GRAY, font=F_LABEL)
y += 24
for et in ["save_draft_report_artifact", "recall_prior_insights"]:
    tool_box(d, c2x+22, y, c2w-44, 30, et)
    y += 36

# Output key
y += 8
d.text((c2x+22, y), "Output:", fill=DARK_GRAY, font=F_LABEL)
y += 24
d.text((c2x+30, y), "combined_final_cited_report", fill=MED_GRAY, font=F_BODY_SM)


# ══════════════════════════════════════════════════════════════════════════════
# SKILL 3: AD CREATIVE
# ══════════════════════════════════════════════════════════════════════════════
c3x = MX + 2*(COL_W+GAP)
c3w = COL_W
y = COL_TOP + 55

agent_box(d, c3x+14, y, c3w-28, 55,
          "ad_content_generator_agent", "LLM Agent  |  gemini-2.5-flash", RED, F_AGENT_MD)

y += 68
# Ad creative pipeline (Actor-Critic)
acp_y = y
acp_h = 175
rrect(d, (c3x+10, acp_y, c3x+c3w-10, acp_y+acp_h), 8,
      fill=lighten(RED, 0.95), outline=RED, width=3)
# Red dashed-style outline for actor-critic
d.text((c3x+18, acp_y+6), "ad_creative_pipeline", fill=darken(RED, 0.15), font=F_BODY_SM)
d.text((c3x+18, acp_y+24), "(AgentTool, Sequential, Actor-Critic)", fill=RED, font=F_BODY_SM)

# Drafter
dy = acp_y + 48
rrect(d, (c3x+18, dy, c3x+c3w-18, dy+50), 6,
      fill=lighten(RED, 0.88), outline=RED, width=1)
d.text((c3x+26, dy+4), "ad_copy_drafter", fill=darken(RED, 0.2), font=F_BODY_SM)
d.text((c3x+26, dy+24), "temp=1.5  |  10-12 drafts", fill=MED_GRAY, font=F_BODY_SM)

small_arrow_down(d, c3x+c3w//2, dy+50+2, dy+60, RED)

# Critic
cy = dy + 62
rrect(d, (c3x+18, cy, c3x+c3w-18, cy+50), 6,
      fill=lighten(RED, 0.88), outline=RED, width=1)
d.text((c3x+26, cy+4), "ad_copy_critic", fill=darken(RED, 0.2), font=F_BODY_SM)
d.text((c3x+26, cy+24), "temp=0.7  |  select 6-8", fill=MED_GRAY, font=F_BODY_SM)

# Visual generation pipeline
y = acp_y + acp_h + 14
vgp_y = y
vgp_h = 165
section_box(d, c3x+10, vgp_y, c3w-20, vgp_h,
            "visual_generation_pipeline", "(AgentTool, Sequential)", RED)

vy = vgp_y + 42
vg_agents = ["visual_concept_drafter", "visual_concept_critic", "visual_concept_finalizer"]
for vi, vn in enumerate(vg_agents):
    inner_agent(d, c3x+18, vy, c3w-36, 30, vn, RED)
    vy += 36
    if vi < len(vg_agents)-1:
        small_arrow_down(d, c3x+c3w//2, vy-8, vy-2, RED)

# Visual generator (AgentTool)
y = vgp_y + vgp_h + 14
vgen_y = y
vgen_h = 130
section_box(d, c3x+10, vgen_y, c3w-20, vgen_h,
            "visual_generator", "(AgentTool)", RED)

# Two tool boxes side by side
tx = c3x + 18
ty = vgen_y + 42
half_w = (c3w - 44) // 2

rrect(d, (tx, ty, tx+half_w-4, ty+72), 6, fill=LIGHT_GRAY, outline=MED_GRAY, width=1)
d.text((tx+6, ty+4), "generate_image", fill=DARK_GRAY, font=F_BODY_SM)
d.text((tx+6, ty+24), "gemini-2.5-", fill=MED_GRAY, font=F_BODY_SM)
d.text((tx+6, ty+42), "flash-image", fill=MED_GRAY, font=F_BODY_SM)

tx2 = tx + half_w + 4
rrect(d, (tx2, ty, tx2+half_w-4, ty+72), 6, fill=LIGHT_GRAY, outline=MED_GRAY, width=1)
d.text((tx2+6, ty+4), "generate_video", fill=DARK_GRAY, font=F_BODY_SM)
d.text((tx2+6, ty+24), "veo-3.1-fast-", fill=MED_GRAY, font=F_BODY_SM)
d.text((tx2+6, ty+42), "generate-001", fill=MED_GRAY, font=F_BODY_SM)

# generate_visuals_batch (autopilot)
y = vgen_y + vgen_h + 14
rrect(d, (c3x+10, y, c3x+c3w-10, y+55), 8,
      fill=lighten(PURPLE, 0.92), outline=PURPLE, width=2)
d.text((c3x+18, y+5), "generate_visuals_batch", fill=PURPLE, font=F_BODY_SM)
d.text((c3x+18, y+25), "parallel asyncio.gather", fill=MED_GRAY, font=F_BODY_SM)
d.text((c3x+18, y+42), "(autopilot mode)", fill=MED_GRAY, font=F_BODY_SM)

# State tools
y += 68
d.text((c3x+22, y), "State Tools:", fill=DARK_GRAY, font=F_LABEL)
y += 24
state_tools = [
    "save_select_ad_copy",
    "save_select_visual_concept",
    "save_img_artifact_key",
    "save_vid_artifact_key",
]
for st in state_tools:
    tool_box(d, c3x+22, y, c3w-44, 28, st)
    y += 34


# ══════════════════════════════════════════════════════════════════════════════
# SKILL 4: AV STUDIO
# ══════════════════════════════════════════════════════════════════════════════
c4x = MX + 3*(COL_W+GAP)
c4w = COL_W
y = COL_TOP + 55

agent_box(d, c4x+14, y, c4w-28, 55,
          "av_editing_studio_agent", "LLM Agent  |  gemini-2.5-flash", PURPLE, F_AGENT_MD)

y += 70
d.text((c4x+22, y), "18 Tools in 4 Categories:", fill=DARK_GRAY, font=F_LABEL)
y += 28

categories = [
    ("Video Generation (7)", [
        "generate_subject_image",
        "generate_transition_frames",
        "generate_clip_with_frames",
        "generate_clips_parallel",
        "extract_frame_from_clip",
        "concatenate_clips",
        "trim_video",
    ]),
    ("Music -- Lyria 2 (4)", [
        "generate_commercial_soundtrack",
        "generate_sound_effects",
        "combine_audio_with_video",
        "add_audio_to_clip",
    ]),
    ("Voice -- Chirp 3 HD (4)", [
        "generate_voice_over",
        "generate_dialogue",
        "generate_branded_tagline",
        "mix_voice_with_audio",
    ]),
    ("Assembly (2)", [
        "save_commercial_artifact",
        "validate_character_consistency",
    ]),
]

for ci, (cat_title, tools) in enumerate(categories):
    ch = 30 + len(tools) * 26
    rrect(d, (c4x+14, y, c4x+c4w-14, y+ch), 8,
          fill=lighten(PURPLE, 0.95), outline=lighten(PURPLE, 0.5), width=1)
    d.text((c4x+22, y+5), cat_title, fill=PURPLE, font=F_BODY_SM)
    ty_ = y + 28
    for t in tools:
        rrect(d, (c4x+22, ty_, c4x+c4w-22, ty_+22), 4,
              fill=LIGHT_GRAY, outline=lighten(MED_GRAY, 0.3), width=1)
        d.text((c4x+28, ty_+2), t, fill=DARK_GRAY, font=F_BODY_SM)
        ty_ += 26
    y += ch + 10

# Additional tool
y += 4
tool_box(d, c4x+22, y, c4w-44, 28, "recommend_audio_style")
y += 38

# Models section
d.text((c4x+22, y), "Models:", fill=DARK_GRAY, font=F_LABEL)
y += 26
models = [
    ("Image", "gemini-2.5-flash-image"),
    ("Video", "veo-3.1-fast-generate-001"),
    ("Voice", "chirp-3-hd"),
    ("Music", "lyria-002"),
]
for mlbl, mval in models:
    rrect(d, (c4x+22, y, c4x+c4w-22, y+28), 5,
          fill=lighten(PURPLE, 0.92), outline=lighten(PURPLE, 0.5), width=1)
    d.text((c4x+30, y+4), f"{mlbl}: {mval}", fill=darken(PURPLE, 0.2), font=F_BODY_SM)
    y += 34

# Production note
y += 10
d.text((c4x+22, y), "Production Flow:", fill=DARK_GRAY, font=F_LABEL)
y += 24
flow_items = [
    "1. Generate subject images",
    "2. Create video clips (Veo)",
    "3. Compose soundtrack (Lyria)",
    "4. Record voice-over (Chirp)",
    "5. Mix & assemble final cut",
    "6. Validate & save artifact",
]
for fi in flow_items:
    d.text((c4x+30, y), fi, fill=MED_GRAY, font=F_BODY_SM)
    y += 22


# ══════════════════════════════════════════════════════════════════════════════
# SKILL 5: FOCUS GROUP
# ══════════════════════════════════════════════════════════════════════════════
c5x = MX + 4*(COL_W+GAP)
c5w = COL_W
y = COL_TOP + 55

agent_box(d, c5x+14, y, c5w-28, 55,
          "focus_group_evaluator_agent", "LLM Agent  |  gemini-2.5-flash", TEAL, F_AGENT_MD)

y += 72
d.text((c5x+22, y), "Tool:", fill=DARK_GRAY, font=F_LABEL)
y += 24
rrect(d, (c5x+14, y, c5x+c5w-14, y+55), 8, fill=LIGHT_GRAY, outline=MED_GRAY, width=1)
d.text((c5x+22, y+6), "analyze_commercial_video", fill=DARK_GRAY, font=F_BODY)
d.text((c5x+22, y+28), "Gemini video understanding", fill=MED_GRAY, font=F_BODY_SM)

y += 68
d.text((c5x+22, y), "Evaluation Criteria:", fill=DARK_GRAY, font=F_LABEL)
y += 28
criteria = [
    "Visual Quality",
    "Narrative Consistency",
    "Trend Relevance",
    "Audience Appeal",
    "Go / No-Go Decision",
]
for cr in criteria:
    rrect(d, (c5x+18, y, c5x+c5w-18, y+36), 7,
          fill=lighten(TEAL, 0.92), outline=TEAL, width=1)
    d.text((c5x+28, y+8), cr, fill=darken(TEAL, 0.2), font=F_BODY)
    y += 42

y += 12
d.text((c5x+22, y), "Evaluation Flow:", fill=DARK_GRAY, font=F_LABEL)
y += 28
flow_steps = [
    "1. Analyze commercial video",
    "2. Scene-by-scene review",
    "3. Score each criterion (1-10)",
    "4. Simulate focus group panel",
    "5. Generate final recommendation",
]
for fi, fs in enumerate(flow_steps):
    rrect(d, (c5x+18, y, c5x+c5w-18, y+32), 6,
          fill=lighten(TEAL, 0.95), outline=lighten(TEAL, 0.5), width=1)
    d.text((c5x+26, y+6), fs, fill=darken(TEAL, 0.2), font=F_BODY_SM)
    y += 38
    if fi < len(flow_steps)-1:
        small_arrow_down(d, c5x+c5w//2, y-8, y-2, TEAL)

y += 16
d.text((c5x+22, y), "Reads from Session State:", fill=DARK_GRAY, font=F_LABEL)
y += 26
read_keys = [
    "commercial_artifact",
    "combined_final_cited_report",
    "target_search_trends",
    "target_yt_trends",
    "brand, target_product",
    "target_audience",
]
for rk in read_keys:
    d.text((c5x+30, y), "- " + rk, fill=MED_GRAY, font=F_BODY_SM)
    y += 22

y += 16
d.text((c5x+22, y), "Output:", fill=DARK_GRAY, font=F_LABEL)
y += 24
d.text((c5x+30, y), "Focus group evaluation", fill=MED_GRAY, font=F_BODY_SM)
y += 20
d.text((c5x+30, y), "with scores & Go/No-Go", fill=MED_GRAY, font=F_BODY_SM)


# ── Data Flow arrows between skills ──────────────────────────────────────────
flow_y = COL_BOT - 30
for i in range(4):
    x1 = MX + i*(COL_W+GAP) + COL_W - 2
    x2 = MX + (i+1)*(COL_W+GAP) + 2
    arrow(d, x1, flow_y, x2, flow_y, MED_GRAY, 2, 8)

fl = "Session State Data Flow"
flw_ = tw(d, fl, F_LABEL)
d.text(((W-flw_)//2, COL_BOT - 58), fl, fill=DARK_GRAY, font=F_LABEL)


# ── Legend ────────────────────────────────────────────────────────────────────
legend_y = COL_BOT + 30
lx_ = MX + 20
d.text((lx_, legend_y), "Legend:", fill=DARK_GRAY, font=F_LEGEND_T)
legend_y += 34

legend_items = [
    (BLUE, "Orchestrator"),
    (ORANGE, "LLM Agent"),
    (GREEN, "Sequential Composition"),
    (PURPLE, "Parallel Composition"),
    (None, "Tool / Function"),     # special: tool style
    (RED, "Actor-Critic Pattern"),  # special: red outline
]

lx_ = MX + 20
bw, bh = 32, 22
for color, label in legend_items:
    if color is None:
        rrect(d, (lx_, legend_y, lx_+bw, legend_y+bh), 5,
              fill=LIGHT_GRAY, outline=MED_GRAY, width=1)
    elif label == "Actor-Critic Pattern":
        rrect(d, (lx_, legend_y, lx_+bw, legend_y+bh), 5,
              fill=lighten(RED, 0.9), outline=RED, width=3)
    else:
        rrect(d, (lx_, legend_y, lx_+bw, legend_y+bh), 5,
              fill=lighten(color, 0.85), outline=color, width=2)
    d.text((lx_+bw+10, legend_y+1), label, fill=DARK_GRAY, font=F_LEGEND)
    lx_ += bw + 14 + tw(d, label, F_LEGEND) + 50


# ── Footer ────────────────────────────────────────────────────────────────────
fy = H - 45
d.text((MX+10, fy), "Google Cloud Platform", fill=BLUE, font=F_LEGEND_T)

# GCP color dots
dot_x = MX + 10 + tw(d, "Google Cloud Platform", F_LEGEND_T) + 20
for di, dc in enumerate([BLUE, RED, YELLOW, GREEN]):
    cx_ = dot_x + di * 20
    d.ellipse([cx_-7, fy+3, cx_+7, fy+17], fill=dc)

ver = "Built with Google ADK 1.25.1  |  Python 3.11+  |  Vertex AI"
vw_ = tw(d, ver, F_FOOTER)
d.text((W - MX - vw_ - 10, fy+2), ver, fill=MED_GRAY, font=F_FOOTER)


# ── Save ──────────────────────────────────────────────────────────────────────
out = "/usr/local/google/home/jwortz/zghost/docs/images/diagrams/agent-pipeline-flow-4k.png"
img.save(out, "PNG", dpi=(300, 300))
print(f"Saved {out}  ({W}x{H})")
