#!/usr/bin/env python3
"""Generate a 4K GCP-branded End-to-End Pipeline Workflow diagram.

Output: 3840 x 2160 px  (16:9, UHD 4K)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ---------- sizing ----------
DPI = 240
W_PX, H_PX = 3840, 2160
W_IN = W_PX / DPI   # 16.0
H_IN = H_PX / DPI   # 9.0

# ---------- GCP brand colours ----------
BLUE    = "#4285F4"
YELLOW  = "#FBBC04"
GREEN   = "#34A853"
RED     = "#EA4335"
PURPLE  = "#A142F4"
TEAL    = "#12B5CB"
WHITE   = "#FFFFFF"
DARK    = "#202124"
GREY_BG = "#F8F9FA"
GREY_LT = "#E8EAED"
GREY_MD = "#9AA0A6"
GREY_DK = "#5F6368"

FONT = "DejaVu Sans"

# Icons that exist in DejaVu Sans
ICON_GEAR   = "\u2699"  # gear ⚙
ICON_SEARCH = "\u2315"  # telephone recorder / use simple ◎ instead
ICON_BOOK   = "\u2261"  # trigram ≡
ICON_ART    = "\u2726"  # four-pointed star ✦ (available in DejaVu)
ICON_FILM   = "\u25B6"  # play triangle ▶
ICON_CHECK  = "\u2714"  # check mark ✔

# Fallback: test which are actually renderable
ICON_SEARCH = "\u25C9"  # circle with dot ◉
ICON_BOOK   = "\u2637"  # trigram / fallback to ≡ \u2261
ICON_ART    = "\u2605"  # black star ★
ICON_FILM   = "\u25B6"  # play ▶


def lighten(hex_color, factor=0.88):
    """Return a lighter version of a hex colour."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


# ── drawing helpers ──

def add_card(ax, x, y, w, h, color):
    """Rounded card with drop-shadow."""
    shadow = FancyBboxPatch(
        (x + 0.04, y - 0.04), w, h,
        boxstyle="round,pad=0.06", facecolor="#00000012",
        edgecolor="none", linewidth=0, zorder=1)
    ax.add_patch(shadow)
    card = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.06",
        facecolor=lighten(color, 0.93),
        edgecolor=color, linewidth=2.2, zorder=2)
    ax.add_patch(card)


def add_header(ax, x, y, w, bar_h, color, icon, stage_num, label):
    """Coloured header bar inside a card."""
    bar = FancyBboxPatch(
        (x + 0.03, y), w - 0.06, bar_h,
        boxstyle="round,pad=0.04", facecolor=color,
        edgecolor="none", linewidth=0, zorder=3)
    ax.add_patch(bar)
    ax.text(x + 0.16, y + bar_h / 2,
            f"{icon}  Stage {stage_num}: {label}",
            fontsize=10, fontweight="bold", color=WHITE,
            fontfamily=FONT, va="center", ha="left", zorder=4)


def add_sublabel(ax, x, y, w, text):
    """Italic sub-label at bottom of a card."""
    ax.text(x + w / 2, y + 0.12, text, fontsize=7,
            fontfamily=FONT, fontstyle="italic", color=GREY_DK,
            va="center", ha="center", zorder=4)


def bullet(ax, x, y, text, fs=7.5, color=DARK, bold=False):
    weight = "bold" if bold else "normal"
    ax.text(x, y, f"\u2022  {text}", fontsize=fs, color=color,
            fontfamily=FONT, va="center", ha="left", fontweight=weight, zorder=4)


def mini_box(ax, x, y, w, h, text, color, fs=6.5, tc=None):
    box = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.025",
        facecolor=lighten(color, 0.72), edgecolor=color,
        linewidth=1.1, zorder=3)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, fontsize=fs,
            fontfamily=FONT, va="center", ha="center",
            color=tc or DARK, fontweight="bold", zorder=4)


def flow_arrow(ax, x1, y1, x2, y2, color=GREY_DK, lw=1.1):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->,head_width=0.07,head_length=0.04",
                                color=color, lw=lw), zorder=5)


def big_arrow(ax, x1, x2, y, color=GREY_MD):
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="->,head_width=0.12,head_length=0.06",
                                color=color, lw=1.8), zorder=5)


# ── main ──

def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])  # fill entire figure
    ax.set_xlim(0, 19.2)
    ax.set_ylim(0, 10.8)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)

    # ── TITLE BAR ──
    tb = FancyBboxPatch(
        (0.25, 9.85), 18.7, 0.72,
        boxstyle="round,pad=0.05", facecolor=DARK,
        edgecolor="none", zorder=2)
    ax.add_patch(tb)
    ax.text(9.6, 10.38, "Marketing Intelligence \u2014 End-to-End Pipeline Workflow",
            fontsize=16, fontweight="bold", color=WHITE,
            fontfamily=FONT, va="center", ha="center", zorder=4)
    ax.text(9.6, 10.05, "v1.0 \u2014 March 2026",
            fontsize=9.5, color=GREY_LT, fontfamily=FONT,
            va="center", ha="center", zorder=4)

    # ── CARD GEOMETRY ──
    cw = 5.6    # card width
    ch = 3.45   # card height
    gx = 0.45   # horizontal gap
    gy = 0.55   # vertical gap
    bar_h = 0.38

    r1_y = 5.95   # row 1 bottom
    r2_y = 1.90   # row 2 bottom
    x0   = 0.35

    pos = [
        (x0,                     r1_y),  # 0 Configure
        (x0 + cw + gx,          r1_y),  # 1 Discover
        (x0 + 2*(cw + gx),      r1_y),  # 2 Research
        (x0,                     r2_y),  # 3 Create
        (x0 + cw + gx,          r2_y),  # 4 Produce
        (x0 + 2*(cw + gx),      r2_y),  # 5 Evaluate
    ]
    colors = [BLUE, YELLOW, GREEN, RED, PURPLE, TEAL]
    icons  = [ICON_GEAR, ICON_SEARCH, "\u2261", ICON_ART, ICON_FILM, ICON_CHECK]
    names  = ["Configure", "Discover", "Research", "Create", "Produce", "Evaluate"]
    subs   = ["User Input", "Trend Discovery",
              "Parallel Market Research (~3 min)",
              "Ad Creative Generation",
              "AV Studio \u2014 Commercial Production",
              "Focus Group Evaluation"]

    for i in range(6):
        cx, cy = pos[i]
        add_card(ax, cx, cy, cw, ch, colors[i])
        add_header(ax, cx, cy + ch - bar_h - 0.05, cw, bar_h,
                   colors[i], icons[i], i+1, names[i])
        add_sublabel(ax, cx, cy, cw, subs[i])

    # ================================================================
    # STAGE 1 — Configure
    # ================================================================
    cx, cy = pos[0]
    ct = cy + ch - bar_h - 0.18
    items = [
        "Brand & Product Definition",
        "Target Audience",
        "Campaign Goals",
        "PDF Guide Upload (PyPDF2)",
        "Key Selling Points",
        "Autopilot / Duration Settings",
    ]
    for j, it in enumerate(items):
        bullet(ax, cx + 0.22, ct - j * 0.32, it, fs=7.5)

    # ================================================================
    # STAGE 2 — Discover
    # ================================================================
    cx, cy = pos[1]
    ct = cy + ch - bar_h - 0.18

    mini_box(ax, cx+0.15, ct-0.18, 2.1, 0.32,
             "BigQuery \u2192 Google Trends", YELLOW, fs=6.5)
    mini_box(ax, cx+2.55, ct-0.18, 2.8, 0.32,
             "YouTube Data API v3 (45 videos)", YELLOW, fs=6.5)
    mini_box(ax, cx+0.15, ct-0.68, 3.5, 0.32,
             "Brand Safety Filter (Gemini 2.5 Flash)", YELLOW, fs=6.5)

    items2 = [
        "User selects Google Search trends",
        "User selects YouTube trends",
        "Trends stored in session state",
    ]
    for j, it in enumerate(items2):
        bullet(ax, cx+0.22, ct-1.12 - j*0.28, it, fs=7)

    # ================================================================
    # STAGE 3 — Research
    # ================================================================
    cx, cy = pos[2]
    ct = cy + ch - bar_h - 0.14

    ax.text(cx + cw/2, ct - 0.02, "3 Parallel Streams",
            fontsize=7.5, fontweight="bold", color=GREEN,
            fontfamily=FONT, ha="center", va="center", zorder=4)

    sw, sh = 1.48, 0.72
    sy = ct - 0.95
    labels_r = [("YouTube\nResearch", "analysis \u2192 plan \u2192 search"),
                ("Google Search\nResearch", "plan \u2192 search"),
                ("Campaign\nResearch", "plan \u2192 search")]
    for k, (lbl, sub) in enumerate(labels_r):
        sx = cx + 0.12 + k * (sw + 0.2)
        mini_box(ax, sx, sy, sw, sh, lbl, GREEN, fs=6.5)
        ax.text(sx + sw/2, sy - 0.14, sub, fontsize=5,
                fontfamily=FONT, color=GREY_DK, ha="center", va="center", zorder=4)

    # Post-merge pipeline
    my = sy - 0.52
    steps = ["Merge", "Evaluate", "Enhance", "Compose"]
    stw = 1.05
    tot = len(steps)*stw + (len(steps)-1)*0.12
    sx0 = cx + (cw - tot)/2
    for k, st in enumerate(steps):
        sxk = sx0 + k*(stw + 0.12)
        mini_box(ax, sxk, my, stw, 0.28, st, GREEN, fs=6.5)
        if k < len(steps)-1:
            flow_arrow(ax, sxk+stw+0.01, my+0.14, sxk+stw+0.11, my+0.14, color=GREEN)

    ax.text(cx + cw/2, my - 0.25,
            "Output: Cited PDF Research Report",
            fontsize=7, fontweight="bold", color=DARK,
            fontfamily=FONT, ha="center", va="center", zorder=4)

    # ================================================================
    # STAGE 4 — Create
    # ================================================================
    cx, cy = pos[3]
    ct = cy + ch - bar_h - 0.16

    # Ad Copy Pipeline
    ax.text(cx+0.20, ct, "Ad Copy Pipeline:", fontsize=7.5,
            fontweight="bold", fontfamily=FONT, color=DARK, zorder=4)
    copy_labels = ["Draft\n(10-12)", "Critique\n(6-8 best)", "User\nSelection"]
    for k, cl in enumerate(copy_labels):
        bx = cx + 0.20 + k * 1.55
        mini_box(ax, bx, ct-0.56, 1.30, 0.42, cl, RED, fs=6)
        if k < len(copy_labels)-1:
            flow_arrow(ax, bx+1.32, ct-0.35, bx+1.53, ct-0.35, color=RED)

    # Visual Concept Pipeline
    ax.text(cx+0.20, ct-0.78, "Visual Concept Pipeline:", fontsize=7.5,
            fontweight="bold", fontfamily=FONT, color=DARK, zorder=4)
    vis_labels = ["Draft", "Critique", "Finalize", "Select"]
    for k, vl in enumerate(vis_labels):
        bx = cx + 0.20 + k * 1.20
        mini_box(ax, bx, ct-1.28, 1.0, 0.38, vl, RED, fs=6)
        if k < len(vis_labels)-1:
            flow_arrow(ax, bx+1.02, ct-1.09, bx+1.18, ct-1.09, color=RED)

    # Generation models
    gy2 = ct - 1.72
    mini_box(ax, cx+0.15, gy2, 2.3, 0.32,
             "Gemini 2.5 Flash Image", RED, fs=6.5)
    mini_box(ax, cx+2.70, gy2, 2.3, 0.32,
             "Veo 3.1 Fast", RED, fs=6.5)
    ax.text(cx+1.30, gy2-0.13, "Image Generation", fontsize=6,
            fontfamily=FONT, color=GREY_DK, ha="center", zorder=4)
    ax.text(cx+3.85, gy2-0.13, "Video Generation", fontsize=6,
            fontfamily=FONT, color=GREY_DK, ha="center", zorder=4)

    # ================================================================
    # STAGE 5 — Produce
    # ================================================================
    cx, cy = pos[4]
    ct = cy + ch - bar_h - 0.12

    # Video Production
    ax.text(cx+0.18, ct, "Video Production:", fontsize=7,
            fontweight="bold", fontfamily=FONT, color=DARK, zorder=4)

    clip_w2, clip_h2 = 0.92, 0.30
    clip_y2 = ct - 0.48
    for k in range(4):
        bx = cx + 0.12 + k * (clip_w2 + 0.18)
        mini_box(ax, bx, clip_y2, clip_w2, clip_h2,
                 f"Clip {k+1} (8s)", PURPLE, fs=5.5)
        if k < 3:
            flow_arrow(ax, bx+clip_w2+0.01, clip_y2+clip_h2/2,
                       bx+clip_w2+0.16, clip_y2+clip_h2/2, color=PURPLE)

    ax.text(cx + cw/2, clip_y2 - 0.16,
            "extract last frame \u2192 next clip  |  concat (ffmpeg) \u2192 trim 30s",
            fontsize=5.5, fontfamily=FONT, color=GREY_DK,
            ha="center", va="center", zorder=4)

    # Audio Production
    ay = clip_y2 - 0.42
    ax.text(cx+0.18, ay, "Audio Production:", fontsize=7,
            fontweight="bold", fontfamily=FONT, color=DARK, zorder=4)

    ay2 = ay - 0.42
    mini_box(ax, cx+0.12, ay2, 1.55, 0.32,
             "Soundtrack (Lyria 2)", PURPLE, fs=6)
    mini_box(ax, cx+1.90, ay2, 1.75, 0.32,
             "Voice-Over (Chirp 3 HD)", PURPLE, fs=6)
    mini_box(ax, cx+3.88, ay2, 1.45, 0.32,
             "Audio Mix", PURPLE, fs=6)

    flow_arrow(ax, cx+1.69, ay2+0.16, cx+1.88, ay2+0.16, color=PURPLE)
    flow_arrow(ax, cx+3.67, ay2+0.16, cx+3.86, ay2+0.16, color=PURPLE)

    # Final output
    oy = ay2 - 0.42
    mini_box(ax, cx+1.1, oy, 3.4, 0.30,
             "Final Commercial \u2192 commercial_30s.mp4", PURPLE, fs=6.5)

    # ================================================================
    # STAGE 6 — Evaluate
    # ================================================================
    cx, cy = pos[5]
    ct = cy + ch - bar_h - 0.16

    ax.text(cx + cw/2, ct, "Simulated Focus Group Scorecard",
            fontsize=8, fontweight="bold", fontfamily=FONT,
            color=DARK, ha="center", zorder=4)

    scores = [
        ("Visual Quality",          8),
        ("Narrative Consistency",    7),
        ("Trend Relevance",         9),
        ("Audience Appeal",         8),
        ("Overall Score",           8),
    ]
    for j, (nm, val) in enumerate(scores):
        sy2 = ct - 0.34 - j * 0.34
        ax.text(cx+0.25, sy2, nm, fontsize=7, fontfamily=FONT,
                color=DARK, va="center", ha="left", zorder=4)
        # draw score bar with rectangles
        bar_x0 = cx + 3.4
        for b in range(10):
            bc = TEAL if b < val else GREY_LT
            rect = FancyBboxPatch(
                (bar_x0 + b*0.19, sy2 - 0.08), 0.16, 0.16,
                boxstyle="round,pad=0.01", facecolor=bc,
                edgecolor="none", linewidth=0, zorder=3)
            ax.add_patch(rect)

    go_y2 = ct - 0.34 - 5 * 0.34
    mini_box(ax, cx+1.3, go_y2 - 0.05, 3.0, 0.35,
             "\u2714  Go / No-Go Recommendation", TEAL, fs=7)

    # ================================================================
    # INTER-CARD ARROWS
    # ================================================================
    # Row 1: 1->2->3
    for i in range(2):
        x1 = pos[i][0] + cw
        x2 = pos[i+1][0]
        ym = pos[i][1] + ch/2
        big_arrow(ax, x1+0.04, x2-0.04, ym, colors[i])

    # Row 2: 4->5->6
    for i in range(3, 5):
        x1 = pos[i][0] + cw
        x2 = pos[i+1][0]
        ym = pos[i][1] + ch/2
        big_arrow(ax, x1+0.04, x2-0.04, ym, colors[i])

    # Stage 3 -> Stage 4 (wrap: down-left-down-right)
    s3x, s3y = pos[2]
    s4x, s4y = pos[3]
    # Right edge of row 1 -> down to gap -> left across -> down into Stage 4
    edge_x = s3x + cw + 0.25  # just right of Stage 3
    gap_y_mid = (s3y + s4y + ch) / 2  # midpoint of vertical gap

    # down from Stage 3 right edge
    ax.plot([edge_x, edge_x], [s3y + ch/2, gap_y_mid],
            color=GREEN, lw=1.8, solid_capstyle="round", zorder=5)
    # left across to above Stage 4 left edge
    left_x = s4x - 0.15
    ax.plot([edge_x, left_x], [gap_y_mid, gap_y_mid],
            color=GREEN, lw=1.8, solid_capstyle="round", zorder=5)
    # down to Stage 4 row
    ax.plot([left_x, left_x], [gap_y_mid, s4y + ch/2],
            color=GREEN, lw=1.8, solid_capstyle="round", zorder=5)
    # arrow into Stage 4
    big_arrow(ax, left_x, s4x - 0.02, s4y + ch/2, GREEN)

    # ================================================================
    # FOOTER BAR
    # ================================================================
    fh = 0.58
    fy = 0.1
    fb = FancyBboxPatch(
        (0.25, fy), 18.7, fh,
        boxstyle="round,pad=0.04", facecolor=DARK,
        edgecolor="none", zorder=2)
    ax.add_patch(fb)

    # Google Cloud (left)
    ax.text(0.55, fy + fh/2, "Google Cloud",
            fontsize=11, fontweight="bold", color=WHITE,
            fontfamily=FONT, va="center", ha="left", zorder=4)

    # Four coloured dots as a mini Google Cloud logo
    dot_colors = [BLUE, RED, YELLOW, GREEN]
    for di, dc in enumerate(dot_colors):
        ax.plot(3.0 + di*0.22, fy + fh/2, 'o', color=dc,
                markersize=5, zorder=4)

    # Service badges — tighter layout to fit duration text
    services = ["Vertex AI", "Cloud Run", "Cloud Storage", "BigQuery", "Secret Mgr"]
    badge_colors_list = [BLUE, GREEN, YELLOW, BLUE, RED]
    bs = 4.2
    bsp = 2.15
    for k, (svc, bc) in enumerate(zip(services, badge_colors_list)):
        bx = bs + k * bsp
        badge = FancyBboxPatch(
            (bx, fy + 0.10), 1.85, 0.38,
            boxstyle="round,pad=0.03", facecolor=bc,
            edgecolor="none", zorder=3)
        ax.add_patch(badge)
        ax.text(bx + 0.925, fy + 0.29, svc,
                fontsize=7.5, fontweight="bold", color=WHITE,
                fontfamily=FONT, va="center", ha="center", zorder=4)

    # Duration (right)
    ax.text(18.7, fy + fh/2,
            "~20 min end-to-end (autopilot)",
            fontsize=8, color=GREY_LT, fontfamily=FONT,
            va="center", ha="right", zorder=4)

    # ── SAVE ──
    out = "/usr/local/google/home/jwortz/zghost/docs/images/diagrams/pipeline-workflow-4k.png"
    fig.savefig(out, dpi=DPI, facecolor=WHITE, edgecolor="none")
    plt.close(fig)
    print(f"Saved: {out}")

    from PIL import Image
    img = Image.open(out)
    print(f"Resolution: {img.size[0]}x{img.size[1]} px")


if __name__ == "__main__":
    main()
