"""Agency-quality PDF report generator using WeasyPrint + Jinja2 + markdown.

Replaces the fpdf2 CampaignPDF class with HTML/CSS-based rendering for
professional typography, inline bold/italic, full Unicode, color badges,
image galleries, and structured focus group cards.
"""

import os
import re
import json
import logging
from datetime import datetime
from jinja2 import Template
import markdown as md

logging.basicConfig(level=logging.INFO)

# ─── HTML + CSS Template ───────────────────────────────────────────────────────

_REPORT_CSS = """
@page {
    size: A4;
    margin: 2cm 2cm 2.5cm 2cm;
    @bottom-center {
        content: counter(page);
        font-size: 8pt;
        color: #999;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    @top-left {
        content: '';
        border-bottom: 2px solid #0033A0;
        width: 100%;
    }
}

@page :first {
    margin: 0;
    @bottom-center { content: none; }
    @top-left { content: none; border: none; }
}

@page back-cover {
    margin: 0;
    @bottom-center { content: none; }
    @top-left { content: none; border: none; }
}

* { box-sizing: border-box; }

body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    color: #1a1a2e;
    line-height: 1.55;
    font-size: 10pt;
}

/* ── Cover Page ── */
.cover {
    page: first;
    width: 100%;
    height: 100%;
    background: linear-gradient(160deg, #0033A0 0%, #001a5c 60%, #000d33 100%);
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 4cm 3.5cm;
    page-break-after: always;
}
.cover .brand-label {
    font-size: 11pt;
    text-transform: uppercase;
    letter-spacing: 4px;
    opacity: 0.6;
    margin-bottom: 0.8em;
}
.cover h1 {
    font-size: 36pt;
    font-weight: 700;
    margin: 0 0 0.2em;
    letter-spacing: -0.5px;
    line-height: 1.1;
}
.cover .tagline {
    font-size: 15pt;
    font-weight: 300;
    opacity: 0.8;
    margin-bottom: 2em;
    line-height: 1.4;
}
.cover .cover-meta {
    font-size: 9pt;
    opacity: 0.5;
    margin-top: auto;
    padding-top: 2em;
    border-top: 1px solid rgba(255,255,255,0.15);
}
.cover img.hero {
    max-width: 220px;
    border-radius: 10px;
    margin-top: 1.5em;
    /* box-shadow not supported by WeasyPrint */
}

/* ── Section Headers ── */
h1 { font-size: 22pt; color: #0033A0; border-bottom: 2.5px solid #0033A0; padding-bottom: 6px; margin-top: 1.2em; margin-bottom: 0.4em; }
h2 { font-size: 15pt; color: #1a73e8; margin-top: 1em; margin-bottom: 0.3em; }
h3 { font-size: 12pt; color: #333; margin-top: 0.8em; margin-bottom: 0.2em; }
h4 { font-size: 10.5pt; color: #555; margin-top: 0.6em; }

p { margin: 0.3em 0; }
strong { color: #0033A0; }
em { color: #444; }

/* ── Info Boxes ── */
.info-box {
    background: #f0f5ff;
    border-left: 4px solid #0033A0;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    margin: 12px 0;
}
.info-box .label { font-weight: 700; font-size: 9pt; color: #0033A0; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.info-box table { margin: 0; }
.info-box td { border: none; padding: 2px 12px 2px 0; font-size: 10pt; }
.info-box td:first-child { font-weight: 600; color: #333; min-width: 100px; }

/* ── Metrics Bar ── */
.metrics-bar {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 16px 0;
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
}
.metric { text-align: center; }
.metric .value { font-size: 22pt; font-weight: 700; color: #0033A0; }
.metric .label { font-size: 8pt; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 16px;
    font-weight: 700;
    font-size: 8.5pt;
    color: white;
    margin: 2px 3px;
}
.badge-green { background: #22c55e; }
.badge-amber { background: #f59e0b; }
.badge-red { background: #ef4444; }
.badge-blue { background: #0033A0; }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; margin: 0.8em 0; font-size: 9.5pt; }
th { background: #0033A0; color: white; padding: 7px 10px; text-align: left; font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 6px 10px; border-bottom: 1px solid #e5e7eb; }
tr:nth-child(even) td { background: #f9fafb; }

/* ── Image Gallery ── */
.gallery { margin: 1em 0; }
.gallery-item {
    break-inside: avoid;
    margin-bottom: 18px;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    overflow: hidden;
}
.gallery-item img { width: 100%; display: block; }
.gallery-item .meta { padding: 10px 14px; }
.gallery-item .meta h3 { margin: 0 0 4px; font-size: 11pt; color: #1a73e8; }
.gallery-item .meta .caption { font-style: italic; color: #666; font-size: 9pt; }
.gallery-item .meta .concept { font-size: 9pt; color: #333; margin-top: 4px; }
.gallery-item .meta .prompt { font-size: 7.5pt; color: #999; margin-top: 6px; border-top: 1px solid #eee; padding-top: 4px; }

/* ── Storyboard ── */
.storyboard-grid { display: flex; flex-wrap: wrap; gap: 12px; margin: 1em 0; }
.storyboard-frame { flex: 1 1 45%; break-inside: avoid; }
.storyboard-frame img { width: 100%; border-radius: 6px; border: 1px solid #ddd; }
.storyboard-frame .scene { font-size: 8pt; color: #666; margin-top: 3px; font-style: italic; }

/* ── Panelist Cards ── */
.panelist-card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px;
    margin: 14px 0;
    break-inside: avoid;
    display: flex;
    gap: 16px;
    background: #fafafa;
}
.panelist-card img.portrait {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid #ddd;
}
.panelist-card .info { flex: 1; }
.panelist-card .name { font-weight: 700; font-size: 12pt; color: #1a1a2e; }
.panelist-card .demographics { font-size: 9pt; color: #666; }
.panelist-card .persona { font-size: 9pt; color: #888; font-style: italic; margin: 4px 0; }
.panelist-card .testimonial { font-size: 10pt; color: #333; margin: 6px 0; padding-left: 12px; border-left: 3px solid #0033A0; }
.panelist-card .scores { margin-top: 6px; }

/* ── Verdict Banner ── */
.verdict-banner {
    padding: 12px 20px;
    border-radius: 8px;
    color: white;
    font-size: 14pt;
    font-weight: 700;
    margin: 10px 0 16px;
}
.verdict-go { background: linear-gradient(135deg, #22c55e, #16a34a); }
.verdict-nogo { background: linear-gradient(135deg, #ef4444, #dc2626); }

/* ── Back Cover ── */
.back-cover {
    page: back-cover;
    width: 100%;
    height: 100%;
    background: #f8f9fa;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    page-break-before: always;
}
.back-cover h2 { color: #0033A0; font-size: 20pt; margin-bottom: 8px; }
.back-cover .powered { color: #888; font-size: 10pt; margin-bottom: 24px; }
.back-cover .summary { color: #666; font-size: 9pt; text-align: center; line-height: 1.8; }
.back-cover .accent-bar { width: 100%; height: 6px; background: #0033A0; position: absolute; bottom: 0; }
"""

_REPORT_TEMPLATE = Template("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{{ css }}</style>
</head>
<body>

{# ── COVER PAGE ── #}
<div class="cover">
  <div class="brand-label">{{ brand_name }}</div>
  <h1 style="color:white; border:none; font-size:36pt;">{{ product_name }}</h1>
  {% if campaign_tagline %}<div class="tagline">{{ campaign_tagline }}</div>{% endif %}
  {% if hero_image %}<img class="hero" src="file://{{ hero_image }}" alt="Product">{% endif %}
  <div class="cover-meta">
    Campaign Report &mdash; {{ date_str }}<br>
    Prepared by Trends &amp; Insights AI Platform
  </div>
</div>

{# ── EXECUTIVE SUMMARY ── #}
<h1>Executive Summary</h1>

{% if campaign_brief %}
<div class="info-box">
  <div class="label">Campaign Brief</div>
  <table>
    {% if campaign_brief.brand %}<tr><td>Brand</td><td>{{ campaign_brief.brand }}</td></tr>{% endif %}
    {% if campaign_brief.product %}<tr><td>Product</td><td>{{ campaign_brief.product }}</td></tr>{% endif %}
    {% if campaign_brief.audience %}<tr><td>Target Audience</td><td>{{ campaign_brief.audience }}</td></tr>{% endif %}
    {% if campaign_brief.selling_points %}<tr><td>Key Features</td><td>{{ campaign_brief.selling_points }}</td></tr>{% endif %}
  </table>
</div>
{% endif %}

<div class="metrics-bar">
  <div class="metric"><div class="value">{{ num_images }}</div><div class="label">Images</div></div>
  <div class="metric"><div class="value">{{ num_videos }}</div><div class="label">Videos</div></div>
  <div class="metric"><div class="value">{{ 'Yes' if has_commercial else 'No' }}</div><div class="label">Commercial</div></div>
  <div class="metric"><div class="value">{{ focus_verdict }}</div><div class="label">Focus Group</div></div>
</div>

{% if key_findings %}
<h2>Key Findings</h2>
<ul>
{% for finding in key_findings %}
  <li>{{ finding | safe }}</li>
{% endfor %}
</ul>
{% endif %}

{# ── TREND DRIVERS ── #}
{% if search_trends or yt_trends %}
<h1>Campaign Context &amp; Trend Drivers</h1>

{% if search_trends %}
<h2>Google Search Trends</h2>
<ul>
{% for t in search_trends %}
  <li>{{ t }}</li>
{% endfor %}
</ul>
{% endif %}

{% if yt_trends %}
<h2>YouTube Trends</h2>
<ul>
{% for t in yt_trends %}
  <li>{{ t }}</li>
{% endfor %}
</ul>
{% endif %}
{% endif %}

{# ── RESEARCH REPORT ── #}
<h1>Research Highlights</h1>
{{ report_html | safe }}

{# ── CREATIVE PORTFOLIO ── #}
{% if images %}
<h1>Creative Portfolio</h1>
<div class="gallery">
{% for img in images %}
  <div class="gallery-item">
    {% if img.local_path %}<img src="file://{{ img.local_path }}" alt="{{ img.headline }}">{% endif %}
    <div class="meta">
      <h3>{{ img.headline }}</h3>
      {% if img.fidelity_score is not none %}
        {% if img.fidelity_score >= 0.7 %}
          <span class="badge badge-green">Gecko Fidelity: {{ "%.2f"|format(img.fidelity_score) }}</span>
        {% elif img.fidelity_score >= 0.5 %}
          <span class="badge badge-amber">Gecko Fidelity: {{ "%.2f"|format(img.fidelity_score) }}</span>
        {% else %}
          <span class="badge badge-red">Gecko Fidelity: {{ "%.2f"|format(img.fidelity_score) }}</span>
        {% endif %}
      {% endif %}
      {% if img.caption %}<div class="caption">{{ img.caption }}</div>{% endif %}
      {% if img.concept %}<div class="concept"><strong>Concept:</strong> {{ img.concept }}</div>{% endif %}
      {% if img.img_prompt %}<div class="prompt"><strong>AI Prompt:</strong> {{ img.img_prompt[:300] }}</div>{% endif %}
    </div>
  </div>
{% endfor %}
</div>
{% endif %}

{# ── COMMERCIAL STORYBOARD ── #}
{% if commercial %}
<h1>Commercial Storyboard</h1>
<div class="info-box">
  <table>
    <tr><td>Title</td><td>{{ commercial.title }}</td></tr>
    <tr><td>Duration</td><td>{{ commercial.duration }}s</td></tr>
    {% if commercial.gcs_uri %}<tr><td>Location</td><td style="font-size:8pt;color:#666;">{{ commercial.gcs_uri }}</td></tr>{% endif %}
  </table>
</div>

{% if commercial.frames %}
<div class="storyboard-grid">
{% for frame in commercial.frames %}
  <div class="storyboard-frame">
    <img src="file://{{ frame.path }}" alt="Frame {{ loop.index }}">
    <div class="scene">{{ frame.description }}</div>
  </div>
{% endfor %}
</div>
{% endif %}

{% if commercial.narrative_arc %}
<h3>Narrative Arc</h3>
<p>{{ commercial.narrative_arc }}</p>
{% endif %}
{% if commercial.target_audience_appeal %}
<h3>Target Audience Appeal</h3>
<p>{{ commercial.target_audience_appeal }}</p>
{% endif %}
{% endif %}

{# ── FOCUS GROUP ── #}
{% if focus_group %}
<h1>Focus Group Evaluation</h1>

{% if focus_group.verdict %}
<div class="verdict-banner {{ 'verdict-go' if focus_group.verdict == 'GO' else 'verdict-nogo' }}">
  Verdict: {{ focus_group.verdict }}
  {% if focus_group.overall_score %} &nbsp;|&nbsp; Overall Score: {{ focus_group.overall_score }}/10{% endif %}
</div>
{% endif %}

{% for p in focus_group.panelists %}
<div class="panelist-card">
  {% if p.portrait_path %}<img class="portrait" src="file://{{ p.portrait_path }}" alt="{{ p.name }}">{% endif %}
  <div class="info">
    <div class="name">{{ p.name }}</div>
    <div class="demographics">
      {% if p.age %}Age {{ p.age }}{% endif %}
      {% if p.occupation %} &mdash; {{ p.occupation }}{% endif %}
    </div>
    {% if p.persona %}<div class="persona">{{ p.persona[:300] }}</div>{% endif %}
    {% if p.testimonial %}<div class="testimonial">&ldquo;{{ p.testimonial }}&rdquo;</div>{% endif %}
    {% if p.scores %}
    <div class="scores">
      {% for metric, val in p.scores.items() %}
        {% if val >= 8 %}
          <span class="badge badge-green">{{ metric|replace('_',' ')|title }}: {{ val }}</span>
        {% elif val >= 6 %}
          <span class="badge badge-amber">{{ metric|replace('_',' ')|title }}: {{ val }}</span>
        {% else %}
          <span class="badge badge-red">{{ metric|replace('_',' ')|title }}: {{ val }}</span>
        {% endif %}
      {% endfor %}
    </div>
    {% endif %}
  </div>
</div>
{% endfor %}

{% if focus_group.suggestions %}
<h2>Improvement Suggestions</h2>
<ul>
{% for s in focus_group.suggestions %}
  <li>{{ s }}</li>
{% endfor %}
</ul>
{% endif %}

{% if focus_group.narrative %}
<h2>Narrative Evaluation</h2>
{{ focus_group.narrative_html | safe }}
{% endif %}
{% endif %}

{# ── PANELIST PROFILES ── #}
{% if panelist_profiles %}
<h1>Focus Group Panelists</h1>
{% for p in panelist_profiles %}
<div class="panelist-card">
  {% if p.portrait_path %}<img class="portrait" src="file://{{ p.portrait_path }}" alt="{{ p.name }}">{% endif %}
  <div class="info">
    <div class="name">{{ p.name }}</div>
    <div class="demographics">Age {{ p.age }}</div>
    {% if p.persona %}<div class="persona">{{ p.persona[:300] }}</div>{% endif %}
    {% if p.video_uri %}<div style="font-size:8pt;color:#1a73e8;margin-top:4px;">Video testimonial recorded</div>{% endif %}
    {% if p.voiceover_uri %}<div style="font-size:8pt;color:#1a73e8;">Voiceover available</div>{% endif %}
  </div>
</div>
{% endfor %}
{% endif %}

{# ── BACK COVER ── #}
<div class="back-cover">
  <h2 style="border:none;">Trends &amp; Insights AI Platform</h2>
  <div class="powered">Powered by Google Gemini, Veo, and Agent Development Kit</div>
  <div class="summary">
    Report Generated: {{ date_str }}<br>
    Total Images: {{ num_images }} &nbsp;|&nbsp; Total Videos: {{ num_videos }}<br>
    Commercial: {{ 'Included' if has_commercial else 'Not produced' }} &nbsp;|&nbsp; Focus Group: {{ focus_verdict }}
  </div>
  <div class="accent-bar"></div>
</div>

</body>
</html>""")


# ─── Helper Functions ──────────────────────────────────────────────────────────

def _extract_key_findings(report_text: str, max_findings: int = 4) -> list[str]:
    """Extract bullet points or first sentences from report for executive summary.

    Returns HTML fragments (inline bold/italic converted).
    """
    findings = []
    for line in report_text.split('\n')[:40]:
        line = line.strip()
        if line.startswith('- ') or line.startswith('* '):
            findings.append(line[2:].strip())
            if len(findings) >= max_findings:
                break
    if not findings:
        sentences = re.split(r'[.!?]\s+', report_text[:600])
        findings = [s.strip() for s in sentences[:max_findings] if len(s.strip()) > 20]
    # Convert inline markdown (**bold**, *italic*) to HTML
    converted = []
    for f in findings:
        f = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', f)
        f = re.sub(r'\*(.+?)\*', r'<em>\1</em>', f)
        converted.append(f)
    return converted


def _format_trends(raw_trends) -> list[str]:
    """Extract trend titles from various state formats."""
    if isinstance(raw_trends, dict):
        items = []
        for v in raw_trends.values():
            if isinstance(v, list):
                for t in v:
                    if isinstance(t, dict):
                        title = t.get("trend_title") or t.get("title") or t.get("video_title") or ""
                        if title:
                            items.append(title)
                    elif isinstance(t, str):
                        items.append(t)
        return items[:10]
    elif isinstance(raw_trends, str):
        return [l.strip() for l in raw_trends.split('\n') if l.strip()][:10]
    return []


def _parse_focus_group(fg_text: str) -> dict | None:
    """Parse focus group evaluation text (JSON or markdown) into structured data."""
    if not fg_text:
        return None

    fg_data = None
    narrative_after = ""
    text = fg_text.strip()

    # Split at closing fence — text after ``` is narrative
    if "```" in text:
        fence_parts = text.split("```")
        if len(fence_parts) >= 3:
            json_block = fence_parts[1]
            narrative_after = fence_parts[2].strip()
        else:
            json_block = fence_parts[1] if len(fence_parts) > 1 else text
        # Strip language hint
        json_block = re.sub(r"^[a-zA-Z_]+\n", "", json_block.strip())
        text = json_block

    try:
        fg_data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    if fg_data and isinstance(fg_data, dict):
        narrative = narrative_after or fg_data.get("narrative_evaluation", "")
        verdict = fg_data.get("go_no_go", "")
        return {
            "verdict": str(verdict).upper() if verdict else "",
            "overall_score": fg_data.get("overall_score", ""),
            "panelists": fg_data.get("panelists", []),
            "suggestions": fg_data.get("improvement_suggestions", []),
            "narrative": narrative,
            "narrative_html": md.markdown(narrative, extensions=["tables", "fenced_code"]) if narrative else "",
        }

    # Fallback: render as markdown HTML
    return {
        "verdict": "",
        "overall_score": "",
        "panelists": [],
        "suggestions": [],
        "narrative": fg_text,
        "narrative_html": md.markdown(fg_text, extensions=["tables", "fenced_code"]),
    }


def _download_portrait(portrait_uri: str, name: str, portrait_dir: str, gcs_bucket: str) -> str | None:
    """Download panelist portrait from GCS, return local path or None."""
    if not portrait_uri:
        return None
    try:
        from .utils import download_image_from_gcs
        safe_n = name.replace(" ", "_").replace(",", "")
        local_path = os.path.join(portrait_dir, f"{safe_n}.png")
        blob_name = portrait_uri.replace(gcs_bucket + "/", "")
        download_image_from_gcs(source_blob_name=blob_name, destination_file_name=local_path)
        return local_path
    except Exception as e:
        logging.warning(f"Could not download portrait for {name}: {e}")
        return None


# ─── Main PDF Generator ───────────────────────────────────────────────────────

def generate_campaign_pdf(
    output_path: str,
    processed_report: str,
    img_artifact_list: list,
    vid_artifact_list: list,
    commercial_artifact: dict,
    focus_group_evaluation: str,
    focus_group_panelists: dict,
    gcs_folder: str = "",
    brand: str = "",
    product: str = "",
    audience: str = "",
    selling_points: str = "",
    target_search_trends: str = "",
    target_yt_trends: str = "",
    img_dir: str = "",
    vid_dir: str = "",
) -> str:
    """Generate agency-quality campaign PDF using WeasyPrint.

    Args:
        output_path: Where to save the PDF file.
        processed_report: Research report markdown text.
        img_artifact_list: List of image artifact metadata dicts.
        vid_artifact_list: List of video artifact metadata dicts.
        commercial_artifact: Commercial metadata dict.
        focus_group_evaluation: Focus group evaluation text.
        focus_group_panelists: Dict with panelist metadata.
        gcs_folder: GCS subfolder for assets.
        brand, product, audience, selling_points: Campaign brief fields.
        target_search_trends, target_yt_trends: Trend data.
        img_dir: Local directory containing downloaded images.
        vid_dir: Local directory containing downloaded videos.

    Returns:
        The output_path of the generated PDF.
    """
    from weasyprint import HTML

    # ── Prepare data ──
    brand_name = brand or "Campaign Report"
    product_name = product or ""
    campaign_tagline = ""

    if not product_name and commercial_artifact and isinstance(commercial_artifact, dict):
        metadata = commercial_artifact.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("title"):
            product_name = metadata["title"]

    if img_artifact_list and len(img_artifact_list) > 0:
        first_img = img_artifact_list[0]
        if first_img.get("headline"):
            campaign_tagline = first_img["headline"]
    if not campaign_tagline and selling_points:
        campaign_tagline = selling_points[:100]

    # Hero image for cover
    hero_image = None
    if img_artifact_list and img_dir:
        first_key = img_artifact_list[0].get("artifact_key", "")
        hero_path = os.path.join(img_dir, first_key)
        if os.path.exists(hero_path):
            hero_image = os.path.abspath(hero_path)

    # Research report → HTML
    report_html = ""
    if processed_report:
        report_html = md.markdown(
            processed_report,
            extensions=["tables", "fenced_code", "nl2br"]
        )

    key_findings = _extract_key_findings(processed_report) if processed_report else []

    # Trends
    search_trends = _format_trends(target_search_trends)
    yt_trends = _format_trends(target_yt_trends)

    # Images with local paths and parsed fidelity
    images = []
    for entry in (img_artifact_list or []):
        artifact_key = entry.get("artifact_key", "")
        local_path = None
        if img_dir and artifact_key:
            candidate = os.path.join(img_dir, artifact_key)
            if os.path.exists(candidate):
                local_path = os.path.abspath(candidate)

        headline = entry.get("headline") or entry.get("concept_name") or entry.get("shot_type", "Untitled")
        headline = headline.replace("_", " ").title()

        fidelity = None
        if entry.get("fidelity_score") is not None:
            try:
                fidelity = float(entry["fidelity_score"])
            except (ValueError, TypeError):
                pass

        images.append({
            "local_path": local_path,
            "headline": headline,
            "caption": entry.get("caption", ""),
            "concept": entry.get("concept", ""),
            "img_prompt": entry.get("img_prompt", ""),
            "fidelity_score": fidelity,
        })

    # Commercial
    commercial = None
    if commercial_artifact and isinstance(commercial_artifact, dict) and commercial_artifact.get("gcs_uri"):
        metadata = commercial_artifact.get("metadata", {}) or {}
        commercial = {
            "title": metadata.get("title", "Campaign Commercial") if isinstance(metadata, dict) else "Campaign Commercial",
            "duration": metadata.get("duration_seconds", "N/A") if isinstance(metadata, dict) else "N/A",
            "gcs_uri": commercial_artifact.get("gcs_uri", ""),
            "narrative_arc": metadata.get("narrative_arc", "") if isinstance(metadata, dict) else "",
            "target_audience_appeal": metadata.get("target_audience_appeal", "") if isinstance(metadata, dict) else "",
            "frames": [],  # Could extract frames here if needed
        }

        # Try to extract storyboard frames
        gcs_uri = commercial_artifact.get("gcs_uri", "")
        if gcs_uri and vid_dir:
            commercial_filename = os.path.basename(gcs_uri)
            commercial_local = os.path.join(vid_dir, commercial_filename)
            if os.path.exists(commercial_local):
                try:
                    from .ad_content_generator_tools import extract_multiple_frames
                    frame_dir = os.path.join(vid_dir, "storyboard_frames")
                    os.makedirs(frame_dir, exist_ok=True)
                    frame_paths = extract_multiple_frames(commercial_local, num_frames=4, output_dir=frame_dir)
                    scenes = metadata.get("scene_descriptions", []) if isinstance(metadata, dict) else []
                    for i, fp in enumerate(frame_paths):
                        commercial["frames"].append({
                            "path": os.path.abspath(fp),
                            "description": scenes[i] if i < len(scenes) else f"Frame {i+1}",
                        })
                except Exception as e:
                    logging.warning(f"Could not extract storyboard frames: {e}")

    # Focus group
    focus_group = _parse_focus_group(focus_group_evaluation)

    # Add portrait paths to focus group panelists
    gcs_bucket = ""
    try:
        gcs_bucket = os.environ.get("BUCKET", "")
    except Exception:
        pass

    if focus_group and focus_group.get("panelists"):
        portrait_dir = os.path.join(os.path.dirname(output_path), "portraits")
        os.makedirs(portrait_dir, exist_ok=True)
        for p in focus_group["panelists"]:
            p["portrait_path"] = None  # Default
            p["scores"] = p.get("scores", {})
            if isinstance(p["scores"], dict):
                # Ensure values are numeric
                p["scores"] = {k: v for k, v in p["scores"].items() if isinstance(v, (int, float))}

    # Focus verdict for metrics bar
    focus_verdict = "N/A"
    if focus_group:
        if focus_group.get("verdict"):
            focus_verdict = focus_group["verdict"]
        elif focus_group_evaluation:
            focus_verdict = "Completed"

    # Panelist profiles from state (separate from focus group JSON)
    panelist_profiles = []
    panelists_raw = focus_group_panelists.get("panelists", []) if isinstance(focus_group_panelists, dict) else []
    if panelists_raw:
        portrait_dir = os.path.join(os.path.dirname(output_path), "portraits")
        os.makedirs(portrait_dir, exist_ok=True)
        for p in panelists_raw:
            # Prefer local portrait path (already on disk) over GCS download
            portrait_path = None
            local_portrait = p.get("portrait_local", "")
            if local_portrait and os.path.exists(local_portrait):
                portrait_path = os.path.abspath(local_portrait)
            else:
                portrait_path = _download_portrait(
                    p.get("portrait_gcs_uri", ""), p.get("name", "Unknown"),
                    portrait_dir, gcs_bucket
                )
            panelist_profiles.append({
                "name": p.get("name", "Unknown"),
                "age": p.get("age", "N/A"),
                "persona": p.get("persona", ""),
                "portrait_path": portrait_path,
                "video_uri": p.get("testimonial_video_gcs_uri", ""),
                "voiceover_uri": p.get("voiceover_gcs_uri", ""),
            })

    # Campaign brief
    campaign_brief = None
    if brand or product or audience or selling_points:
        campaign_brief = {
            "brand": brand, "product": product,
            "audience": audience, "selling_points": selling_points,
        }

    # ── Render HTML ──
    html_string = _REPORT_TEMPLATE.render(
        css=_REPORT_CSS,
        brand_name=brand_name,
        product_name=product_name,
        campaign_tagline=campaign_tagline,
        hero_image=hero_image,
        date_str=datetime.now().strftime('%B %d, %Y'),
        campaign_brief=campaign_brief,
        num_images=len(img_artifact_list or []),
        num_videos=len(vid_artifact_list or []),
        has_commercial=bool(commercial),
        focus_verdict=focus_verdict,
        key_findings=key_findings,
        search_trends=search_trends,
        yt_trends=yt_trends,
        report_html=report_html,
        images=images,
        commercial=commercial,
        focus_group=focus_group,
        panelist_profiles=panelist_profiles,
    )

    # ── Generate PDF ──
    HTML(string=html_string).write_pdf(output_path)
    logging.info(f"Generated agency-quality PDF: {output_path}")
    return output_path
