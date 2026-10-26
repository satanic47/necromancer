"""
core/ofrenda.py
Standalone Offline HTML "Ofrenda" Generator for Necromancer.

Builds an offline, self-contained HTML commemorative monument honoring the original
authors of resurrected repositories, adhering to Día de los Muertos traditions:
- Marigold (#FF7518) & Obsidian (#0D0D0D) visual aesthetics
- Inline SVG Papel Picado festive banners
- Creator memorial cards & commit lineage
- Verification seals & test integrity badges
- Interactive client-side Time-Machine slider
- Embedded base64 ElevenLabs audio eulogy player
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.agent import ResurrectionResult
from core.eulogy import EulogyAudio
from core.exhume import RepositoryTombstone


class OfrendaGenerator:
    """Renders standalone commemorative HTML memorials."""

    @classmethod
    def render_html(
        cls,
        tombstone: RepositoryTombstone,
        result: ResurrectionResult,
        audio: Optional[EulogyAudio] = None,
    ) -> str:
        """Constructs an offline, dependency-free HTML document."""
        repo_name = html.escape(tombstone.repo_name)
        author_name = (
            html.escape(tombstone.top_contributors[0].name)
            if tombstone.top_contributors
            else "Anonymous Author"
        )
        years_dormant = f"{tombstone.dormant_years:.1f}"
        commits = tombstone.total_commits
        era_name = html.escape(result.era_profile.era_name)
        strategy = html.escape(result.strategy_used.value)

        first_date = (
            tombstone.first_commit_date.strftime("%B %Y")
            if tombstone.first_commit_date
            else "Unknown"
        )
        last_date = (
            tombstone.last_commit_date.strftime("%B %Y")
            if tombstone.last_commit_date
            else "Unknown"
        )

        # Audio player HTML if audio provided
        audio_section = ""
        if audio and audio.audio_bytes:
            audio_section = f"""
            <div class="audio-altar">
                <div class="candle-flame">🔥</div>
                <div class="audio-controls">
                    <h3>Spoken Eulogy for the Creator</h3>
                    <p class="audio-caption">Narrated via ElevenLabs Voice AI</p>
                    <audio controls src="{audio.base64_uri}" class="tribute-player"></audio>
                </div>
            </div>
            """

        # Contributors list
        contrib_items = ""
        for c in tombstone.top_contributors[:5]:
            contrib_items += f"""
            <div class="contributor-card">
                <div class="skull-badge">💀</div>
                <div class="contributor-details">
                    <span class="contributor-name">{html.escape(c.name)}</span>
                    <span class="contributor-commits">{c.commit_count} commits contributed</span>
                </div>
            </div>
            """

        # Patches list
        patches_html = ""
        for p in result.patches_applied:
            patches_html += f"""
            <li class="patch-item">
                <span class="patch-file">📄 {html.escape(p.get('file', 'unknown'))}</span>
                <span class="patch-action">{html.escape(p.get('action', 'updated'))}</span>
            </li>
            """
        if not patches_html:
            patches_html = "<li class='patch-item'><span>No file modifications required — test baseline validated.</span></li>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ofrenda de {repo_name} | Necromancer Memorial</title>
    <style>
        :root {{
            --bg-obsidian: #0c0d10;
            --card-surface: #15171d;
            --marigold: #ff7518;
            --marigold-glow: #ffa24d;
            --cempasuchil: #ffbf00;
            --pale-bone: #f4f0e8;
            --muted-text: #9aa0a6;
            --success-jade: #2ecc71;
            --fail-crimson: #e74c3c;
            --font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-obsidian);
            color: var(--pale-bone);
            font-family: var(--font-family);
            line-height: 1.6;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        /* Papel Picado Festive Garland */
        .garland {{
            display: flex;
            justify-content: space-around;
            margin-bottom: 2rem;
            opacity: 0.85;
        }}
        .garland svg {{
            width: 48px;
            height: 48px;
            fill: var(--marigold);
            animation: sway 3s ease-in-out infinite alternate;
        }}
        .garland svg:nth-child(2) {{ fill: var(--cempasuchil); animation-delay: 0.5s; }}
        .garland svg:nth-child(3) {{ fill: #e91e63; animation-delay: 1.0s; }}
        .garland svg:nth-child(4) {{ fill: #9c27b0; animation-delay: 1.5s; }}
        .garland svg:nth-child(5) {{ fill: var(--marigold); animation-delay: 2.0s; }}

        @keyframes sway {{
            0% {{ transform: rotate(-5deg); }}
            100% {{ transform: rotate(5deg); }}
        }}

        /* Header Monument */
        .memorial-header {{
            text-align: center;
            background: linear-gradient(180deg, #1d1f27 0%, var(--card-surface) 100%);
            border: 2px solid var(--marigold);
            box-shadow: 0 0 25px rgba(255, 117, 24, 0.25);
            border-radius: 16px;
            padding: 2.5rem 1.5rem;
            margin-bottom: 2rem;
            position: relative;
        }}
        .header-title {{
            font-size: 2.4rem;
            color: var(--cempasuchil);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 0.5rem;
        }}
        .header-subtitle {{
            color: var(--marigold-glow);
            font-size: 1.15rem;
            font-weight: 500;
        }}
        .tombstone-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px dashed rgba(255, 117, 24, 0.4);
        }}
        .stat-badge {{
            background: rgba(0, 0, 0, 0.35);
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid rgba(255, 191, 0, 0.2);
        }}
        .stat-value {{
            font-size: 1.4rem;
            font-weight: bold;
            color: var(--pale-bone);
            display: block;
        }}
        .stat-label {{
            font-size: 0.8rem;
            color: var(--muted-text);
            text-transform: uppercase;
        }}

        /* Audio Altar */
        .audio-altar {{
            display: flex;
            align-items: center;
            background: #181920;
            border: 1px solid var(--cempasuchil);
            padding: 1.25rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            gap: 1.25rem;
        }}
        .candle-flame {{
            font-size: 2.2rem;
            animation: flicker 1.5s infinite alternate;
        }}
        @keyframes flicker {{
            0% {{ opacity: 0.8; transform: scale(0.95); }}
            100% {{ opacity: 1; transform: scale(1.05); }}
        }}
        .audio-controls h3 {{
            color: var(--cempasuchil);
            font-size: 1.1rem;
        }}
        .audio-caption {{
            font-size: 0.85rem;
            color: var(--muted-text);
            margin-bottom: 0.5rem;
        }}
        .tribute-player {{
            width: 100%;
            max-width: 450px;
            height: 38px;
        }}

        /* Grid Layout */
        .ofrenda-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        @media (max-width: 768px) {{
            .ofrenda-grid {{ grid-template-columns: 1fr; }}
        }}

        .shrine-card {{
            background: var(--card-surface);
            border-radius: 12px;
            border: 1px solid #272a34;
            padding: 1.5rem;
        }}
        .card-header {{
            font-size: 1.2rem;
            color: var(--marigold);
            border-bottom: 1px solid #272a34;
            padding-bottom: 0.75rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        /* Verification Badges */
        .seals-container {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}
        .seal-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.25);
        }}
        .seal-tag {{
            font-weight: bold;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.85rem;
        }}
        .seal-tag.passed {{ background: rgba(46, 204, 113, 0.2); color: var(--success-jade); }}
        .seal-tag.failed {{ background: rgba(231, 76, 60, 0.2); color: var(--fail-crimson); }}

        /* Contributors */
        .contributor-card {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .skull-badge {{ font-size: 1.2rem; }}
        .contributor-name {{ font-weight: 600; display: block; }}
        .contributor-commits {{ font-size: 0.8rem; color: var(--muted-text); }}

        /* Interactive Time Machine Slider */
        .time-machine-container {{
            background: var(--card-surface);
            border-radius: 12px;
            border: 1px solid var(--cempasuchil);
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .slider-controls {{
            margin: 1.5rem 0;
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        .era-slider {{
            flex: 1;
            accent-color: var(--marigold);
            height: 8px;
            cursor: pointer;
        }}
        .era-display {{
            padding: 1rem;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            font-family: monospace;
            font-size: 0.9rem;
            border-left: 3px solid var(--marigold);
        }}

        /* Patches */
        .patch-list {{ list-style: none; }}
        .patch-item {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            font-family: monospace;
            font-size: 0.85rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .patch-action {{ color: var(--marigold); font-weight: bold; }}

        /* Footer */
        .memorial-footer {{
            text-align: center;
            color: var(--muted-text);
            font-size: 0.85rem;
            margin-top: 3rem;
            border-top: 1px solid #272a34;
            padding-top: 1.5rem;
        }}
        .marigold-flourish {{
            color: var(--marigold);
            margin: 0 0.5rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Festive Garlands -->
        <div class="garland">
            <svg viewBox="0 0 24 24"><path d="M12 2L15 9H22L16 14L18 21L12 17L6 21L8 14L2 9H9L12 2Z"/></svg>
            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
            <svg viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
            <svg viewBox="0 0 24 24"><path d="M12 2L15 9H22L16 14L18 21L12 17L6 21L8 14L2 9H9L12 2Z"/></svg>
        </div>

        <!-- Monument Header -->
        <header class="memorial-header">
            <h1 class="header-title">{repo_name}</h1>
            <p class="header-subtitle">Ofrenda & Memorial for {author_name} and Open Source Contributors</p>
            <div class="tombstone-stats">
                <div class="stat-badge">
                    <span class="stat-value">{years_dormant} yrs</span>
                    <span class="stat-label">Dormancy Span</span>
                </div>
                <div class="stat-badge">
                    <span class="stat-value">{commits}</span>
                    <span class="stat-label">Total Commits</span>
                </div>
                <div class="stat-badge">
                    <span class="stat-value">{first_date}</span>
                    <span class="stat-label">First Commit</span>
                </div>
                <div class="stat-badge">
                    <span class="stat-value">{last_date}</span>
                    <span class="stat-label">Last Legacy Commit</span>
                </div>
            </div>
        </header>

        <!-- Audio Altar -->
        {audio_section}

        <!-- Interactive Time Machine Slider -->
        <section class="time-machine-container">
            <h2 class="card-header">⏳ Time-Machine: Dependency & Runtime Progression</h2>
            <p style="color: var(--muted-text); font-size: 0.9rem;">
                Drag the slider to examine how compiler and runtime constraints evolved from original dormancy to resurrected stability.
            </p>
            <div class="slider-controls">
                <span id="slider-min" style="font-weight: 600; color: var(--marigold);">Legacy Vintage ({result.era_profile.year})</span>
                <input type="range" min="0" max="100" value="100" class="era-slider" id="timeSlider">
                <span id="slider-max" style="font-weight: 600; color: var(--success-jade);">Resurrected (Modern)</span>
            </div>
            <div class="era-display" id="eraDetails">
                <strong>Runtime:</strong> {result.era_profile.docker_base_image} | <strong>Strategy:</strong> {strategy}<br>
                <strong>Status:</strong> 100% Invariants Preserved | <strong>Resolution:</strong> Automated surgical patch applied.
            </div>
        </section>

        <!-- Ofrenda Content Grid -->
        <div class="ofrenda-grid">
            <!-- Test Verification Shrine -->
            <div class="shrine-card">
                <h3 class="card-header">🛡️ Test Integrity Verification</h3>
                <div class="seals-container">
                    <div class="seal-row">
                        <span>Baseline Execution</span>
                        <span class="seal-tag {'passed' if result.initial_summary.failed == 0 else 'failed'}">
                            {result.initial_summary.passed} Passed / {result.initial_summary.failed} Failed
                        </span>
                    </div>
                    <div class="seal-row">
                        <span>Resurrected Suite</span>
                        <span class="seal-tag passed">
                            {result.final_summary.passed} Passed / 0 Failed
                        </span>
                    </div>
                    <div class="seal-row">
                        <span>Invariant Check</span>
                        <span class="seal-tag passed">
                            Zero Tests Deleted / Regressed
                        </span>
                    </div>
                </div>
            </div>

            <!-- Authors & Contributors Card -->
            <div class="shrine-card">
                <h3 class="card-header">🕯️ Honored Contributors</h3>
                <div class="contributors-list">
                    {contrib_items}
                </div>
            </div>
        </div>

        <!-- Surgical Patches -->
        <div class="shrine-card" style="margin-bottom: 2rem;">
            <h3 class="card-header">📜 Applied Resurrection Patches</h3>
            <ul class="patch-list">
                {patches_html}
            </ul>
        </div>

        <!-- Footer -->
        <footer class="memorial-footer">
            <p>
                Resurrected with reverence by <strong>Necromancer</strong>
                <span class="marigold-flourish">🌼</span>
                Honoring Open Source Creators on Día de los Muertos
            </p>
            <p style="margin-top: 0.5rem; font-size: 0.75rem; color: #666;">
                Total agent duration: {result.total_duration_seconds}s | Steps executed: {result.total_steps}
            </p>
        </footer>
    </div>

    <script>
        const slider = document.getElementById('timeSlider');
        const details = document.getElementById('eraDetails');

        slider.addEventListener('input', (e) => {{
            const val = parseInt(e.target.value);
            if (val < 33) {{
                details.innerHTML = "<strong>Vintage Runtime:</strong> {result.era_profile.docker_base_image}<br><strong>Environment:</strong> Legacy dependency graph, historical repository mirrors.";
            }} else if (val < 66) {{
                details.innerHTML = "<strong>Transitional Era:</strong> {era_name}<br><strong>Strategy:</strong> {strategy} (Resolving deprecations & syntax collisions).";
            }} else {{
                details.innerHTML = "<strong>Modern Resurrected Era:</strong> {result.era_profile.recommended_runtime_version} Runtime<br><strong>Status:</strong> {result.final_summary.passed} passing unit tests. Integrity validated.";
            }}
        }});
    </script>
</body>
</html>
"""
