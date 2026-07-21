"""FPL ruleset loader and validity checks.

The ruleset lives in config/rules/{season}.yaml. FPL changes rules nearly every
season, so every section carries `verify_at_season_launch`; the engine exposes
`unverified_sections()` and downstream phases (optimizer) must refuse to run
while sections are unverified, unless explicitly overridden.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RULES_DIR = PROJECT_ROOT / "config" / "rules"


class Ruleset:
    def __init__(self, raw: dict[str, Any]):
        self.raw = raw

    @classmethod
    def load(cls, season: str = "2026-27") -> "Ruleset":
        path = RULES_DIR / f"{season}.yaml"
        return cls(yaml.safe_load(path.read_text()))

    @property
    def season(self) -> str:
        return self.raw["season"]

    def unverified_sections(self) -> list[str]:
        """Sections still flagged verify_at_season_launch."""
        return [
            key
            for key, value in self.raw.items()
            if isinstance(value, dict) and value.get("verify_at_season_launch")
        ]

    def is_verified(self) -> bool:
        return self.raw.get("verified_against_official", False) and not self.unverified_sections()

    def squad_shape(self) -> dict[str, int]:
        squad = self.raw["squad"]
        return {
            "GKP": squad["goalkeepers"],
            "DEF": squad["defenders"],
            "MID": squad["midfielders"],
            "FWD": squad["forwards"],
        }

    def policy(self, name: str) -> Any:
        return self.raw["policies"][name]


if __name__ == "__main__":
    rules = Ruleset.load()
    print(f"season: {rules.season}")
    print(f"verified: {rules.is_verified()}")
    print(f"unverified sections: {rules.unverified_sections()}")
