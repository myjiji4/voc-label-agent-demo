# -*- coding: utf-8 -*-
"""Taxonomy loading and validation."""
import json
import os
from typing import Dict, List, Tuple

DEFAULT_TAXONOMY = os.path.join(os.path.dirname(__file__), "..", "..", "data", "taxonomy.json")


class Taxonomy(object):
    def __init__(self, path=None):
        path = path or os.environ.get("VOC_TAXONOMY") or DEFAULT_TAXONOMY
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.data = data
        self.groups = [g["l0"] for g in data["groups"]]
        self.labels = {}  # l0 -> [l1]
        self.label_to_l0 = {}
        self.label_to_l0s = {}
        for g in data["groups"]:
            self.labels[g["l0"]] = list(g["labels"])
            for lab in g["labels"]:
                self.label_to_l0.setdefault(lab, g["l0"])
                self.label_to_l0s.setdefault(lab, set()).add(g["l0"])
        self.aliases = {}
        for fam in data.get("aliases", []):
            for m in fam.get("members", []):
                self.aliases[m] = fam["canonical"]

    def canonical(self, l1: str) -> str:
        l1 = (l1 or "").strip()
        return self.aliases.get(l1, l1)

    def l0_for(self, l1: str):
        vals = self.l0s_for(l1)
        return next(iter(vals)) if vals else None

    def l0s_for(self, l1: str):
        return self.label_to_l0s.get(self.canonical(l1), set())

    def is_valid_pair(self, l0: str, l1: str) -> bool:
        l1 = self.canonical(l1)
        return (l0 or "").strip() in self.l0s_for(l1)

    def all_pairs(self) -> List[Tuple[str, str]]:
        out = []
        for l0, labels in self.labels.items():
            for l1 in labels:
                out.append((l0, l1))
        return out

    def prompt_block(self) -> str:
        lines = []
        for g in self.data["groups"]:
            lines.append("- %s: %s" % (g["l0"], " / ".join(g["labels"])))
        return "\n".join(lines)
