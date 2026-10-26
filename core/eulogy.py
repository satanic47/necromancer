"""
core/eulogy.py
ElevenLabs Eulogy & Commemorative Narration Engine for Necromancer.

Generates a heartfelt, poetic tribute honoring the original open-source authors
in the tradition of Día de los Muertos, and produces a spoken narration using
ElevenLabs Text-to-Speech API.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from core.exhume import RepositoryTombstone


DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" - warm, clear narration


@dataclass
class EulogyAudio:
    text: str
    audio_bytes: bytes
    mime_type: str = "audio/mpeg"

    @property
    def base64_uri(self) -> str:
        """Returns a self-contained data URI for offline HTML audio embedding."""
        b64 = base64.b64encode(self.audio_bytes).decode("ascii")
        return f"data:{self.mime_type};base64,{b64}"


class EulogyEngine:
    """Creates commemorative eulogies and synthesizes narration via ElevenLabs."""

    @classmethod
    def compose_text(cls, tombstone: RepositoryTombstone) -> str:
        """Composes a poetic tribute to the creators of the dormant repository."""
        primary_author = "an unknown craftsperson"
        if tombstone.top_contributors and tombstone.top_contributors[0].name.strip():
            primary_author = tombstone.top_contributors[0].name.strip()

        years_str = f"{tombstone.dormant_years:.1f}" if tombstone.dormant_years > 0 else "many"
        commits_str = f"{tombstone.total_commits}"

        return (
            f"Here lies {tombstone.repo_name}, a repository lovingly crafted by {primary_author} "
            f"and contributors, resting in dormancy for over {years_str} years across {commits_str} commits. "
            f"In the spirit of the Día de los Muertos Ofrenda, we celebrate the foundation you built. "
            f"Though frameworks faded and compilers changed, your architecture endures. "
            f"We honor your code, breathing new light into your legacy. Rest well, creator—your work lives on."
        )

    @classmethod
    def synthesize_speech(
        cls,
        text: str,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        client: Optional[httpx.Client] = None,
    ) -> EulogyAudio:
        """Synthesizes text into audio using ElevenLabs TTS."""
        key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
        v_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)

        # Fallback to synthetic silent/mock audio if no API key or in offline tests
        if not key or key.startswith("mock") or key == "EMPTY":
            # 1-second mock silent MP3 frame
            mock_frame = b"\xff\xfb\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00" * 32
            return EulogyAudio(text=text, audio_bytes=mock_frame)

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{v_id}"
        headers = {
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.65,
                "similarity_boost": 0.85,
            },
        }

        try:
            if client:
                res = client.post(url, headers=headers, json=payload, timeout=30.0)
                res.raise_for_status()
                return EulogyAudio(text=text, audio_bytes=res.content)
            else:
                with httpx.Client(timeout=30.0) as http_client:
                    res = http_client.post(url, headers=headers, json=payload)
                    res.raise_for_status()
                    return EulogyAudio(text=text, audio_bytes=res.content)
        except Exception:
            # Graceful fallback to synthetic audio frame on network failure
            fallback_bytes = b"\xff\xfb\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00" * 16
            return EulogyAudio(text=text, audio_bytes=fallback_bytes)
