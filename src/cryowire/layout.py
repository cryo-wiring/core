"""Directory layout management for cryowire data repositories.

Standard layout::

    <data_root>/
    ├── components.yaml
    ├── templates/
    └── <cryo>/
        ├── <year>/
        │   ├── cd001/
        │   │   ├── metadata.yaml
        │   │   ├── chip.yaml
        │   │   ├── control.yaml
        │   │   ├── readout_send.yaml
        │   │   ├── readout_return.yaml
        │   │   └── cooldown.yaml
        │   └── cd002/
        └── <year>/
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class YearGroup:
    """A year directory containing cooldown subdirectories."""
    year: str
    cooldowns: list[str] = field(default_factory=list)


@dataclass
class CryoEntry:
    """A cryostat with its year groups."""
    name: str
    years: list[YearGroup] = field(default_factory=list)


_CD_RE = re.compile(r"^cd(\d{3,})$")


class CryoLayout:
    """Manages the ``cryo/year/cdNNN`` directory hierarchy.

    Parameters
    ----------
    data_root
        Root directory of the data repository.
    """

    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root.resolve()

    # ── Listing ──────────────────────────────────────────────────────────

    def list_cryos(self) -> list[CryoEntry]:
        """List all cryostats with their year groups and cooldowns."""
        if not self.data_root.exists():
            return []
        entries: list[CryoEntry] = []
        for d in sorted(self.data_root.iterdir()):
            if not d.is_dir() or d.name.startswith(".") or d.name == "templates":
                continue
            years = self._list_years(d)
            if years:
                entries.append(CryoEntry(name=d.name, years=years))
        return entries

    def _list_years(self, cryo_dir: Path) -> list[YearGroup]:
        """List year groups within a cryostat directory."""
        groups: list[YearGroup] = []
        for yr in sorted(cryo_dir.iterdir(), reverse=True):
            if not yr.is_dir() or yr.name.startswith("."):
                continue
            cds = sorted(
                cd.name
                for cd in yr.iterdir()
                if cd.is_dir() and (cd / "cooldown.yaml").exists()
            )
            if cds:
                groups.append(YearGroup(year=yr.name, cooldowns=cds))
        return groups

    # ── Path resolution ──────────────────────────────────────────────────

    def cryo_path(self, cryo: str) -> Path:
        """Return the path to a cryostat directory."""
        return self.data_root / cryo

    def cooldown_path(self, cryo: str, year: str, cooldown: str) -> Path:
        """Return the path to a cooldown directory."""
        return self.data_root / cryo / year / cooldown

    # ── Cooldown ID generation ───────────────────────────────────────────

    def next_cooldown_id(self, cryo: str, year: str) -> str:
        """Determine the next ``cdNNN`` within a year directory."""
        year_dir = self.data_root / cryo / year
        max_n = 0
        if year_dir.exists():
            for d in year_dir.iterdir():
                if not d.is_dir():
                    continue
                m = _CD_RE.match(d.name)
                if m:
                    max_n = max(max_n, int(m.group(1)))
        return f"cd{max_n + 1:03d}"
