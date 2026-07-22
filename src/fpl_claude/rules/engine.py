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

    def sell_price(self, buy_cost: int, current_cost: int) -> int:
        """Sell price in API tenths of £m under budget.sell_price_rule.

        half_profit_rounded_down: sell = buy + floor(profit / 2); losses are
        passed through in full (sell = current when current <= buy).
        """
        rule = self.raw["budget"]["sell_price_rule"]
        if rule != "half_profit_rounded_down":
            raise NotImplementedError(f"unknown sell_price_rule: {rule}")
        profit = current_cost - buy_cost
        if profit <= 0:
            return current_cost
        return buy_cost + profit // 2


if __name__ == "__main__":
    rules = Ruleset.load()
    print(f"season: {rules.season}")
    print(f"verified: {rules.is_verified()}")
    print(f"unverified sections: {rules.unverified_sections()}")
