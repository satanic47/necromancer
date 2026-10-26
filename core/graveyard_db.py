"""
core/graveyard_db.py
Graveyard & Hall of Fame Database Interface for Necromancer.

Targets MongoDB Atlas as a Hackathon / DEV Partner integration to persist
resurrected repository tombstones, audit metrics, and commemorative ofrendas.
Operates with graceful local JSON/in-memory fallback when no MongoDB connection string is provided.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.agent import ResurrectionResult
from core.exhume import RepositoryTombstone


class GraveyardDatabase:
    """Manages persistence of resurrected repositories in MongoDB Atlas or local store."""

    def __init__(self, mongo_uri: Optional[str] = None):
        self.mongo_uri = mongo_uri or os.getenv("MONGODB_URI")
        self.client = None
        self.collection = None
        self._local_archive: List[Dict[str, Any]] = []

        if self.mongo_uri and not os.getenv("TESTING"):
            try:
                import pymongo
                self.client = pymongo.MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
                db = self.client.get_database(os.getenv("MONGODB_DATABASE", "necromancer"))
                self.collection = db.get_collection("ofrendas")
            except Exception:
                self.client = None
                self.collection = None

    def record_ofrenda(
        self,
        tombstone: RepositoryTombstone,
        result: ResurrectionResult,
        eulogy_text: str,
    ) -> Dict[str, Any]:
        """Saves a commemorative ofrenda record into the database."""
        entry = {
            "repo_name": tombstone.repo_name,
            "primary_language": tombstone.primary_language,
            "dormant_years": tombstone.dormant_years,
            "total_commits": tombstone.total_commits,
            "lead_author": tombstone.top_contributors[0].name if tombstone.top_contributors else "Unknown",
            "era_name": result.era_profile.era_name,
            "strategy_used": result.strategy_used.value,
            "success": result.success,
            "eulogy_text": eulogy_text,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.collection is not None:
            try:
                self.collection.insert_one(dict(entry))
            except Exception:
                pass

        self._local_archive.append(entry)
        return entry

    def list_hall_of_fame(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent resurrected monuments from MongoDB or local store."""
        if self.collection is not None:
            try:
                docs = list(self.collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
                if docs:
                    return docs
            except Exception:
                pass

        return self._local_archive[-limit:]
