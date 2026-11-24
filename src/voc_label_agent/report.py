# -*- coding: utf-8 -*-
"""Small markdown report helpers."""
from typing import Any, Dict


def metrics_table(m: Dict[str, Any]) -> str:
    lines = [
        "| Metric | Value |",
        "|---|---:|",
        "| N | %s |" % m.get("n"),
        "| Exact set match | %.2f%% (95%% CI %.2f–%.2f) |" % (
            100 * m.get("exact_set_match", 0), 100 * m["exact_set_match_ci95"][0], 100 * m["exact_set_match_ci95"][1]),
        "| Primary group match | %.2f%% |" % (100 * m.get("primary_group_match", 0)),
        "| L0 accuracy (primary) | %.2f%% |" % (100 * m.get("l0_accuracy_primary", 0)),
        "| Review-type accuracy | %.2f%% |" % (100 * m.get("review_type_accuracy", 0)),
        "| L1 micro-F1 | %.4f |" % m.get("l1_micro_f1", 0),
        "| L1 macro-F1 | %.4f |" % m.get("l1_macro_f1", 0),
        "| Invalid output rate | %.2f%% |" % (100 * m.get("invalid_output_rate", 0)),
        "| Review queue rate | %.2f%% |" % (100 * m.get("review_queue_rate", 0)),
        "| Error capture rate | %.2f%% |" % (100 * m.get("error_capture_rate", 0)),
        "| Review queue precision | %.2f%% |" % (100 * m.get("review_queue_precision", 0)),
    ]
    return "\n".join(lines)


def compare_table(c: Dict[str, Any]) -> str:
    lines = ["| Metric | Baseline | Agent | Delta |", "|---|---:|---:|---:|"]
    for k, v in c.items():
        lines.append("| %s | %s | %s | %+.4f |" % (k, v.get("baseline"), v.get("agent"), v.get("delta", 0)))
    return "\n".join(lines)


def slice_table(title: str, d: Dict[str, Any]) -> str:
    lines = ["### %s" % title, "", "| Slice | N | Exact set match |", "|---|---:|---:|"]
    for k, v in d.items():
        lines.append("| %s | %s | %.2f%% |" % (k, v.get("n"), 100 * v.get("exact_set_match", 0)))
    return "\n".join(lines)


def risk_table(rows) -> str:
    lines = ["### Risk–coverage (agent)", "",
             "| Confidence threshold | Coverage | Exact set match | Queue rate | Error capture |",
             "|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append("| %.2f | %.1f%% | %.1f%% | %.1f%% | %.1f%% |" % (
            r["threshold"], 100 * r["coverage"], 100 * r["exact_set_match"],
            100 * r["queue_rate"], 100 * r["error_capture_rate"]))
    return "\n".join(lines)
