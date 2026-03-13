#!/usr/bin/env python3
"""Generate GCP Solution Architecture diagram using matplotlib."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(20, 15), dpi=150)
ax.set_xlim(0, 20)
ax.set_ylim(0, 15)
ax.axis('off')
fig.patch.set_facecolor('#FAFBFC')

# Helper functions
def draw_box(ax, x, y, w, h, color, text, fontsize=11, text_color='white', alpha=0.95, bold=True):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                         facecolor=color, edgecolor='#555555', linewidth=1.2, alpha=alpha,
                         zorder=3)
    ax.add_patch(box)
    # shadow
    shadow = FancyBboxPatch((x+0.04, y-0.04), w, h, boxstyle="round,pad=0.15",
                            facecolor='#00000015', edgecolor='none', zorder=2)
    ax.add_patch(shadow)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fontsize,
            color=text_color, fontweight=weight, zorder=4, wrap=True,
            fontfamily='sans-serif')

def draw_region_box(ax, x, y, w, h, color, label, label_fontsize=12):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2",
                         facecolor=color, edgecolor='#888888', linewidth=1.5,
                         alpha=0.3, zorder=1)
    ax.add_patch(box)
    ax.text(x + 0.25, y + h - 0.3, label, ha='left', va='top', fontsize=label_fontsize,
            color='#333333', fontweight='bold', fontfamily='sans-serif', zorder=4)

def draw_arrow(ax, x1, y1, x2, y2, color='#666666', style='->', lw=1.5):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, connectionstyle='arc3,rad=0.05'),
                zorder=5)

# Title
ax.text(10, 14.5, 'Trends & Insights - GCP Solution Architecture', ha='center', va='center',
        fontsize=22, fontweight='bold', color='#1A237E', fontfamily='sans-serif')
ax.text(10, 14.05, 'Multi-Agent Marketing Intelligence System on Google Cloud', ha='center', va='center',
        fontsize=14, color='#555555', fontfamily='sans-serif')

# --- Top: Frontend ---
draw_box(ax, 6.5, 12.8, 7, 0.85, '#7B1FA2', 'Gemini Enterprise / Discovery Engine Frontend', fontsize=13)

# --- Google Cloud VPC Region ---
draw_region_box(ax, 3.5, 5.5, 13, 6.5, '#E3F2FD', 'Google Cloud VPC')

# VPC inner components
draw_box(ax, 6.5, 10.2, 7, 0.85, '#1565C0', 'Vertex AI Agent Engine\n(Core Orchestrator)', fontsize=12)

draw_box(ax, 4.2, 8.2, 4.5, 0.85, '#00838F', 'Vertex AI Memory Bank\n(Campaign Memory)', fontsize=11)
draw_box(ax, 11.3, 8.2, 4.5, 0.85, '#2E7D32', 'Cloud Storage\n(Media Artifacts)', fontsize=11)
draw_box(ax, 7.5, 6.2, 5, 0.85, '#E65100', 'Secret Manager\n(API Keys & Credentials)', fontsize=11)

# --- Right: Generative AI Models ---
draw_region_box(ax, 17, 8.5, 2.7, 3.8, '#E8EAF6', 'Generative AI Models')
draw_box(ax, 17.2, 10.8, 2.3, 0.7, '#1976D2', 'Gemini 3 Flash\n(Text/Reasoning)', fontsize=9.5)
draw_box(ax, 17.2, 9.8, 2.3, 0.7, '#1976D2', 'Gemini 3 Pro\n(Image Gen)', fontsize=9.5)
draw_box(ax, 17.2, 8.8, 2.3, 0.7, '#1976D2', 'Veo 3.1\n(Video Gen)', fontsize=9.5)

# --- Left: External APIs ---
draw_region_box(ax, 0.3, 8.5, 2.7, 3.8, '#FFF3E0', 'External APIs')
draw_box(ax, 0.5, 10.8, 2.3, 0.7, '#D84315', 'YouTube\nData API', fontsize=9.5)
draw_box(ax, 0.5, 9.8, 2.3, 0.7, '#D84315', 'Google Search\n& Trends', fontsize=9.5)
draw_box(ax, 0.5, 8.8, 2.3, 0.7, '#D84315', 'Web Scraping\n(httpx)', fontsize=9.5)

# --- Arrows ---
# Frontend -> Agent Engine
draw_arrow(ax, 10, 12.8, 10, 11.1, '#7B1FA2', lw=2)

# Agent Engine -> Memory Bank
draw_arrow(ax, 8, 10.2, 6.5, 9.1, '#00838F', lw=1.8)

# Agent Engine -> Cloud Storage
draw_arrow(ax, 12, 10.2, 13.5, 9.1, '#2E7D32', lw=1.8)

# Agent Engine -> Secret Manager
draw_arrow(ax, 10, 10.2, 10, 7.1, '#E65100', lw=1.5)

# Agent Engine -> Gen AI Models
draw_arrow(ax, 13.5, 10.6, 17.0, 10.6, '#1976D2', lw=2)

# Agent Engine -> External APIs
draw_arrow(ax, 6.5, 10.6, 3.0, 10.6, '#D84315', lw=2)

# --- Data Flow Summary ---
draw_region_box(ax, 1.5, 0.8, 17, 4.2, '#F5F5F5', 'Data Flow Summary')

flow_items = [
    ("1.", "User Queries", "Gemini Enterprise", "Agent Engine", '#7B1FA2'),
    ("2.", "Agent Engine", "Generative Models", "(Text, Images, Video)", '#1976D2'),
    ("3.", "Generated Media", "Cloud Storage", "(GCS Buckets)", '#2E7D32'),
    ("4.", "Agent State & Memory", "Memory Bank", "(Campaign Insights)", '#00838F'),
]

for i, (num, src, dst, detail, color) in enumerate(flow_items):
    ypos = 4.2 - i * 0.85
    ax.text(2.2, ypos, num, fontsize=13, fontweight='bold', color=color, va='center', fontfamily='sans-serif')
    ax.text(2.8, ypos, f'{src}  -->  {dst}  {detail}', fontsize=12, color='#333333', va='center', fontfamily='sans-serif')

# Google Cloud branding text
ax.text(1.0, 0.3, 'Google', fontsize=14, fontweight='bold', color='#4285F4', va='center', fontfamily='sans-serif')
ax.text(2.85, 0.3, 'Cloud', fontsize=14, fontweight='bold', color='#EA4335', va='center', fontfamily='sans-serif')

# Version tag
ax.text(19.5, 0.3, 'v3.0 | 2026', fontsize=10, color='#999999', ha='right', va='center', fontfamily='sans-serif')

plt.tight_layout(pad=0.5)
plt.savefig('/usr/local/google/home/jwortz/zghost/gcp_architecture_diagram.png',
            dpi=150, bbox_inches='tight', facecolor='#FAFBFC')
plt.close()
print("GCP architecture diagram saved successfully.")
