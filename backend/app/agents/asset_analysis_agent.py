from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Asset


ARCHETYPE_HINTS = [
    "Authority Figure",
    "Executive",
    "Attorney",
    "Detective",
    "Journalist",
    "Teacher",
    "Nurse",
    "Parent",
    "Neighbor",
    "Best Friend",
    "Comedy",
    "Dramatic Guest Star",
    "Blue Collar",
    "Political Leader",
]


class AssetAnalysisAgent:
    def __init__(self, db: Session) -> None:
        self.db = db

    def analyze(self, asset: Asset) -> Asset:
        text = f"{asset.asset_name} {asset.description or ''} {asset.original_filename or ''}".lower()
        suggested_archetypes = [name for name in ARCHETYPE_HINTS if name.lower() in text]
        if not suggested_archetypes:
            if asset.asset_type == "Headshot":
                suggested_archetypes = ["Authority Figure", "Dramatic Guest Star"]
            elif asset.asset_type == "Reel":
                suggested_archetypes = ["Dramatic Guest Star"]
            else:
                suggested_archetypes = ["Professional"]
        filename_tags = [
            part
            for part in Path(asset.original_filename or asset.asset_name).stem.replace("-", "_").split("_")
            if len(part) > 2
        ]
        suggested_tags = sorted(set([asset.asset_type.lower(), *filename_tags, *asset.tags]))
        asset.ai_suggested_tags = suggested_tags
        asset.ai_suggested_archetypes = suggested_archetypes
        asset.analysis_status = "suggested"
        asset.analysis_explanation = (
            "Suggestions were generated from the asset type, filename, description, and current tags. "
            "The user-approved tags and archetypes remain the source of truth."
        )
        self.db.commit()
        self.db.refresh(asset)
        return asset

