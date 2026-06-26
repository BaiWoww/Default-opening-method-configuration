"""Data models for file associations."""
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class Preset:
    name: str
    path: str
    args: str = ""

    def command_line(self) -> str:
        if self.args.strip():
            return f'"{self.path}" {self.args}'
        return f'"{self.path}" "%1"'


@dataclass
class ExtensionConfig:
    ext: str
    presets: List[Preset] = field(default_factory=list)
    custom: bool = False
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "presets": [asdict(p) for p in self.presets],
            "custom": self.custom,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, ext: str, data: dict) -> "ExtensionConfig":
        presets = [Preset(**p) for p in data.get("presets", [])]
        return cls(
            ext=ext,
            presets=presets,
            custom=bool(data.get("custom", False)),
            description=data.get("description", ""),
        )
