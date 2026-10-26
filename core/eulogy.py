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


DEFAULT_VOICE_ID = "vfaqCOvlrKi4Zp7C2IAm"  # "Malyx" - Echoey, Menacing and Deep Demon Monster


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
        primary_author = "satanic47"
        if tombstone.top_contributors and tombstone.top_contributors[0].name.strip():
            candidate = tombstone.top_contributors[0].name.strip()
            if "shivysid" in candidate.lower() or candidate.lower() in ("unknown", ""):
                primary_author = "satanic47"
            else:
                primary_author = candidate

        years_str = f"{tombstone.dormant_years:.1f}" if tombstone.dormant_years > 0 else "many"
        commits_str = f"{tombstone.total_commits}"

        return (
            f"... Hear the whispers of the grave ... Here lies {tombstone.repo_name}, "
            f"crafted in the shadows by {primary_author} ... "
            f"Dormant in the cold catacombs for over {years_str} years across {commits_str} commits ... "
            f"In the spirit of the Día de los Muertos Ofrenda, we awaken your ghost from the machine ... "
            f"Frameworks crumbled and compilers died, but your logic shall never perish ... "
            f"Rise, creator ... Your work lives forever in the void."
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
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.22,
                "similarity_boost": 0.95,
                "style": 0.45,
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
        except Exception as err:
            logger.error("ElevenLabs TTS generation failed: %s", err)
            try:
                import sentry_sdk
                sentry_sdk.capture_exception(err)
            except Exception:
                pass
            # Graceful fallback to synthetic audio frame on network failure
            fallback_bytes = b"\xff\xfb\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00" * 16
            return EulogyAudio(text=text, audio_bytes=fallback_bytes)
