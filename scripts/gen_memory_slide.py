#!/usr/bin/env python3
"""Generate a 4K executive slide showing Memory Bank data flow in the zghost system."""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# ── Colors ──────────────────────────────────────────────────────────────────
BG          = "#0F1923"       # dark navy
CARD_BG     = "#172A3A"       # slightly lighter card
CARD_BORDER = "#2A4A5E"       # subtle border
GBLUE       = "#4285F4"       # Google blue
GGREEN      = "#34A853"       # Google green
GYELLOW     = "#FBBC04"       # Google yellow
GRED        = "#EA4335"       # Google red
GOLD        = "#F5B041"       # amber / gold for insights
LIGHT       = "#E8EAED"       # light text
DIM         = "#9AA0A6"       # dimmed text
WHITE       = "#FFFFFF"
CYAN        = "#5EB8FF"       # accent cyan
MEMORY_GLOW = "#4285F4"

# ── Figure setup (4K: 3840x2160 @ 150 DPI) ─────────────────────────────────
fig = plt.figure(figsize=(25.6, 14.4), dpi=150, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 56.25)  # 16:9 aspect
ax.set_facecolor(BG)
ax.axis("off")

FONT = "DejaVu Sans"

# ── Helper: rounded card ────────────────────────────────────────────────────
def draw_card(x, y, w, h, color=CARD_BG, border=CARD_BORDER, radius=0.8, alpha=0.85, zorder=2):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=color, edgecolor=border, linewidth=1.2,
        alpha=alpha, zorder=zorder,
        transform=ax.transData,
    )
    ax.add_patch(box)
    return box

# ── Helper: curved arrow ───────────────────────────────────────────────────
def draw_arrow(x1, y1, x2, y2, color=GBLUE, style="->", lw=2.2, zorder=5,
               connectionstyle="arc3,rad=0.12", alpha=0.9):
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        connectionstyle=connectionstyle,
        arrowstyle=style,
        mutation_scale=18,
        color=color,
        linewidth=lw,
        alpha=alpha,
        zorder=zorder,
    )
    ax.add_patch(arrow)
    return arrow

# ── Helper: bullet text ────────────────────────────────────────────────────
def bullets(x, y, items, fontsize=7.2, color=DIM, spacing=1.6, zorder=10):
    for i, item in enumerate(items):
        ax.text(x, y - i * spacing, f"  {item}", fontsize=fontsize,
                fontfamily=FONT, color=color, va="top", zorder=zorder)

# ═════════════════════════════════════════════════════════════════════════════
# TITLE
# ═════════════════════════════════════════════════════════════════════════════
ax.text(50, 53.5, "Memory-Augmented Intelligence", fontsize=26, fontweight="bold",
        fontfamily=FONT, color=WHITE, ha="center", va="top", zorder=10)
ax.text(50, 50.8, "How Campaign Insights Compound Over Time",
        fontsize=13, fontfamily=FONT, color=GOLD, ha="center", va="top",
        style="italic", zorder=10)

# thin gold rule under title
ax.plot([20, 80], [49.8, 49.8], color=GOLD, linewidth=0.8, alpha=0.5, zorder=10)

# ═════════════════════════════════════════════════════════════════════════════
# COLUMN 1 — CAMPAIGN EXECUTION (left)
# ═════════════════════════════════════════════════════════════════════════════
col1_x, col1_y, col1_w, col1_h = 3, 14, 25, 33
draw_card(col1_x, col1_y, col1_w, col1_h, alpha=0.7)
ax.text(col1_x + col1_w/2, col1_y + col1_h - 1.8, "Campaign Execution",
        fontsize=13, fontweight="bold", fontfamily=FONT, color=GBLUE,
        ha="center", va="top", zorder=10)
ax.plot([col1_x + 3, col1_x + col1_w - 3],
        [col1_y + col1_h - 3.5, col1_y + col1_h - 3.5],
        color=GBLUE, linewidth=0.6, alpha=0.4, zorder=10)

# Sub-cards inside column 1
sub_cards = [
    ("Research Pipeline", GBLUE, 39.5, [
        "Parallel trend analysis (YT + Search)",
        "Web research with grounded citations",
        "Quality evaluation & refinement",
        "Cited report generation",
    ]),
    ("Ad Creative Studio", GGREEN, 29, [
        "Draft \u2192 Critique \u2192 Finalize workflow",
        "Image gen (Gemini 3.1 Flash)",
        "Video gen (Veo 3.1)",
        "Gecko fidelity evaluation",
    ]),
    ("Focus Group & AV Studio", GYELLOW, 18.5, [
        "Audience reaction simulation",
        "Commercial editing & narration",
        "Music scoring & sound design",
    ]),
]

for title, accent, card_y, items in sub_cards:
    draw_card(col1_x + 1.5, card_y - 0.5, col1_w - 3, 9.2,
              color="#1A2F3F", border=accent, alpha=0.6, radius=0.5)
    ax.text(col1_x + 3, card_y + 7.5, title, fontsize=9.2, fontweight="bold",
            fontfamily=FONT, color=accent, va="top", zorder=10)
    bullets(col1_x + 3.5, card_y + 5.8, items, fontsize=6.8, spacing=1.55)

# ═════════════════════════════════════════════════════════════════════════════
# COLUMN 2 — MEMORY BANK (center, prominent)
# ═════════════════════════════════════════════════════════════════════════════
mb_x, mb_y, mb_w, mb_h = 33, 14, 34, 33

# Outer glow effect (multiple layers)
for i, a in enumerate([0.03, 0.05, 0.08]):
    g = i * 0.8
    draw_card(mb_x - g, mb_y - g, mb_w + 2*g, mb_h + 2*g,
              color=MEMORY_GLOW, border=MEMORY_GLOW, alpha=a, radius=1.2, zorder=1)

draw_card(mb_x, mb_y, mb_w, mb_h, color="#0D2137", border=GBLUE, alpha=0.92, radius=1.0)

# Cloud icon (simplified shape with text)
ax.text(mb_x + mb_w/2, mb_y + mb_h - 2.0, "\u2601",
        fontsize=30, color=GBLUE, ha="center", va="top", alpha=0.25, zorder=9)
ax.text(mb_x + mb_w/2, mb_y + mb_h - 2.2,
        "Vertex AI Memory Bank", fontsize=14, fontweight="bold",
        fontfamily=FONT, color=WHITE, ha="center", va="top", zorder=10)
ax.text(mb_x + mb_w/2, mb_y + mb_h - 4.5,
        "Persistent Cross-Session Memory", fontsize=9, fontfamily=FONT,
        color=CYAN, ha="center", va="top", zorder=10)

ax.plot([mb_x + 4, mb_x + mb_w - 4],
        [mb_y + mb_h - 5.8, mb_y + mb_h - 5.8],
        color=GBLUE, linewidth=0.6, alpha=0.4, zorder=10)

# Memory scope dimensions
scope_y_start = mb_y + mb_h - 7.5
scope_cards = [
    ("Campaign Insights", GOLD, [
        "Audience preferences & reactions",
        "Successful messaging patterns",
        "Trend correlations & timing",
        "Competitive landscape data",
    ]),
    ("Skill Memories", GGREEN, [
        "Effective image/video prompts",
        "Research techniques that worked",
        "Ad copy patterns with high impact",
        "Quality scores (Gecko fidelity)",
    ]),
    ("Quality Metrics", CYAN, [
        "Fidelity scores over time",
        "Research depth benchmarks",
        "Creative performance tracking",
    ]),
]

for idx, (title, accent, items) in enumerate(scope_cards):
    sy = scope_y_start - idx * 8.5
    draw_card(mb_x + 2, sy - 0.3, mb_w - 4, 7.2,
              color="#132A3E", border=accent, alpha=0.55, radius=0.5)
    # Colored dot + title
    ax.plot(mb_x + 3.5, sy + 5.8, 'o', color=accent, markersize=5, zorder=10)
    ax.text(mb_x + 5, sy + 5.8, title, fontsize=9, fontweight="bold",
            fontfamily=FONT, color=accent, va="center", zorder=10)
    bullets(mb_x + 5, sy + 4.2, items, fontsize=6.5, spacing=1.35)

# ═════════════════════════════════════════════════════════════════════════════
# COLUMN 3 — INTELLIGENCE AMPLIFICATION (right)
# ═════════════════════════════════════════════════════════════════════════════
col3_x, col3_y, col3_w, col3_h = 72, 14, 25, 33
draw_card(col3_x, col3_y, col3_w, col3_h, alpha=0.7)
ax.text(col3_x + col3_w/2, col3_y + col3_h - 1.8,
        "Intelligence Amplification", fontsize=13, fontweight="bold",
        fontfamily=FONT, color=GGREEN, ha="center", va="top", zorder=10)
ax.plot([col3_x + 3, col3_x + col3_w - 3],
        [col3_y + col3_h - 3.5, col3_y + col3_h - 3.5],
        color=GGREEN, linewidth=0.6, alpha=0.4, zorder=10)

right_cards = [
    ("preload_memory", GBLUE, 39.5, [
        "Session starts \u2192 Memory Bank queried",
        "ADK built-in tool on root_agent",
        "Injects relevant past insights",
        "Zero-effort context enrichment",
    ]),
    ("recall_prior_insights", GOLD, 29, [
        "Mid-research Memory Bank query",
        "Similarity search by brand + product",
        "Retrieves campaign + skill memories",
        "Feeds into enhanced_combined_searcher",
    ]),
    ("Compounding Returns", GGREEN, 18.5, [
        "Research quality improves each run",
        "Creative prompts refine over time",
        "Cross-brand pattern recognition",
        "Institutional knowledge persists",
    ]),
]

for title, accent, card_y, items in right_cards:
    draw_card(col3_x + 1.5, card_y - 0.5, col3_w - 3, 9.2,
              color="#1A2F3F", border=accent, alpha=0.6, radius=0.5)
    ax.text(col3_x + 3, card_y + 7.5, title, fontsize=9.2, fontweight="bold",
            fontfamily=FONT, color=accent, va="top", zorder=10)
    bullets(col3_x + 3.5, card_y + 5.8, items, fontsize=6.8, spacing=1.55)

# ═════════════════════════════════════════════════════════════════════════════
# ARROWS — Data Flow
# ═════════════════════════════════════════════════════════════════════════════

# Left -> Center (SAVE): Campaign outputs flow into Memory Bank
arrow_save_y = 38
draw_arrow(28, arrow_save_y, 33, arrow_save_y,
           color=GOLD, lw=3.0, connectionstyle="arc3,rad=0.0", style="-|>")
ax.text(30.5, arrow_save_y + 1.5, "SAVE", fontsize=8, fontweight="bold",
        fontfamily=FONT, color=GOLD, ha="center", va="bottom", zorder=10,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=BG, edgecolor=GOLD, alpha=0.7, linewidth=0.8))

# save_research_to_memory label
ax.text(30.5, arrow_save_y - 1.0, "save_research\n_to_memory", fontsize=5.8,
        fontfamily=FONT, color=DIM, ha="center", va="top", zorder=10, style="italic")

# Left -> Center (SAVE): Creative skill memory
arrow_save2_y = 27
draw_arrow(28, arrow_save2_y, 33, arrow_save2_y,
           color=GGREEN, lw=2.5, connectionstyle="arc3,rad=0.0", style="-|>")
ax.text(30.5, arrow_save2_y + 1.5, "SAVE", fontsize=7, fontweight="bold",
        fontfamily=FONT, color=GGREEN, ha="center", va="bottom", zorder=10,
        bbox=dict(boxstyle="round,pad=0.25", facecolor=BG, edgecolor=GGREEN, alpha=0.7, linewidth=0.8))
ax.text(30.5, arrow_save2_y - 1.0, "save_creative\n_skill_to_memory", fontsize=5.8,
        fontfamily=FONT, color=DIM, ha="center", va="top", zorder=10, style="italic")

# Center -> Right (RECALL): Memory Bank feeds next campaign
arrow_recall_y = 38
draw_arrow(67, arrow_recall_y, 72, arrow_recall_y,
           color=GBLUE, lw=3.0, connectionstyle="arc3,rad=0.0", style="-|>")
ax.text(69.5, arrow_recall_y + 1.5, "RECALL", fontsize=8, fontweight="bold",
        fontfamily=FONT, color=GBLUE, ha="center", va="bottom", zorder=10,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=BG, edgecolor=GBLUE, alpha=0.7, linewidth=0.8))
ax.text(69.5, arrow_recall_y - 1.0, "preload_memory\n(session start)", fontsize=5.8,
        fontfamily=FONT, color=DIM, ha="center", va="top", zorder=10, style="italic")

# Center -> Right (RECALL): Mid-research recall
arrow_recall2_y = 27
draw_arrow(67, arrow_recall2_y, 72, arrow_recall2_y,
           color=GOLD, lw=2.5, connectionstyle="arc3,rad=0.0", style="-|>")
ax.text(69.5, arrow_recall2_y + 1.5, "QUERY", fontsize=7, fontweight="bold",
        fontfamily=FONT, color=GOLD, ha="center", va="bottom", zorder=10,
        bbox=dict(boxstyle="round,pad=0.25", facecolor=BG, edgecolor=GOLD, alpha=0.7, linewidth=0.8))
ax.text(69.5, arrow_recall2_y - 1.0, "recall_prior\n_insights (research)", fontsize=5.8,
        fontfamily=FONT, color=DIM, ha="center", va="top", zorder=10, style="italic")

# Feedback loop: Right -> Left (curved, top)
draw_arrow(84, 47.5, 16, 47.5,
           color=GGREEN, lw=2.0, connectionstyle="arc3,rad=-0.25", style="-|>", alpha=0.6)
ax.text(50, 49, "Next campaign starts smarter",
        fontsize=8, fontfamily=FONT, color=GGREEN, ha="center", va="bottom",
        alpha=0.8, zorder=10, style="italic")

# ═════════════════════════════════════════════════════════════════════════════
# BOTTOM — Key Callouts
# ═════════════════════════════════════════════════════════════════════════════
callout_y = 9.5
callouts = [
    ("Each campaign makes the\nnext one smarter", GOLD, 16),
    ("Cross-brand learning: insights from\none brand inform future campaigns", GBLUE, 50),
    ("Automatic fact extraction\nand consolidation", GGREEN, 84),
]

for text, color, cx in callouts:
    draw_card(cx - 13, callout_y - 2.5, 26, 6.5,
              color="#0D1F2D", border=color, alpha=0.5, radius=0.6)
    # Diamond bullet
    ax.plot(cx, callout_y + 3, marker="D", color=color, markersize=6, zorder=10)
    ax.text(cx, callout_y + 1.0, text, fontsize=8.2, fontfamily=FONT,
            color=LIGHT, ha="center", va="center", zorder=10, linespacing=1.5)

# ═════════════════════════════════════════════════════════════════════════════
# BOTTOM-LEFT — Google Cloud branding
# ═════════════════════════════════════════════════════════════════════════════
brand_y = 2.5
ax.text(3, brand_y, "Google", fontsize=10, fontweight="bold",
        fontfamily=FONT, color=GBLUE, va="center", zorder=10)
ax.text(10.8, brand_y, "Cloud", fontsize=10, fontweight="bold",
        fontfamily=FONT, color=GRED, va="center", zorder=10)
ax.text(17, brand_y, "  |  Vertex AI  \u00b7  Agent Development Kit  \u00b7  Gemini",
        fontsize=7.5, fontfamily=FONT, color=DIM, va="center", zorder=10)

# BOTTOM-RIGHT — system name
ax.text(97, brand_y, "zghost", fontsize=9, fontfamily=FONT, color=DIM,
        ha="right", va="center", alpha=0.5, zorder=10, style="italic")

# ═════════════════════════════════════════════════════════════════════════════
# SAVE
# ═════════════════════════════════════════════════════════════════════════════
output_path = "/usr/local/google/home/jwortz/zghost/docs/memory_insights_flow.png"
fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor(),
            pad_inches=0.3)
plt.close(fig)
print(f"Saved: {output_path}")
