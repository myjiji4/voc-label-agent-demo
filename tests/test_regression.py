# -*- coding: utf-8 -*-
import json
import os

from voc_label_agent.schema import confidence_score, extract_json
from voc_label_agent.eval import risk_coverage
from voc_label_agent.taxonomy import Taxonomy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAX = Taxonomy(os.path.join(ROOT, "data", "taxonomy.json"))


def test_extract_json_multiline_chinese_quotes():
    text = '''{
  "review_type": "差评",
  "facts_original": [
    "客服团队形同虚设（Non-existent customer service team）",
    "工作日联系仍只收到“周末非办公时间”的自动回复"
  ],
  "facts_translated": [
    "客服团队形同虚设",
    "工作日只收到“周末非办公时间”自动回复"
  ],
  "translation_issues": [],
  "groups": [
    {"l0": "客服问题", "l1": "无法联系客服", "evidence": "no possibility", "confidence": 0.9}
  ],
  "needs_human_review": false,
  "review_reasons": []
}'''
    obj = extract_json(text)
    assert obj["groups"][0]["l1"] == "无法联系客服"


def test_confidence_score_penalties():
    base = {"groups": [{"l0": "物流问题", "l1": "发货慢", "confidence": 0.9}],
            "review_reasons": [], "translation_issues": [], "needs_human_review": False}
    assert confidence_score(base) == 0.9

    two = {"groups": [{"l0": "物流问题", "l1": "发货慢", "confidence": 0.9},
                      {"l0": "客服问题", "l1": "客服无人回复", "confidence": 0.9}],
           "review_reasons": [], "translation_issues": [], "needs_human_review": False}
    assert confidence_score(two) < 0.9

    bad = dict(base)
    bad["review_reasons"] = ["evidence_not_found"]
    assert confidence_score(bad) < 0.6


def test_risk_coverage_shape():
    rows = [
        {"gold": {"gold_groups": [{"l0": "物流问题", "l1": "发货慢"}]},
         "pred": {"groups": [{"l0": "物流问题", "l1": "发货慢", "confidence": 0.95}],
                  "review_reasons": [], "translation_issues": [], "needs_human_review": False}},
        {"gold": {"gold_groups": [{"l0": "物流问题", "l1": "发货慢"}]},
         "pred": {"groups": [{"l0": "物流问题", "l1": "发货慢", "confidence": 0.55}],
                  "review_reasons": [], "translation_issues": [], "needs_human_review": False}},
        {"gold": {"gold_groups": [{"l0": "客服问题", "l1": "客服无人回复"}]},
         "pred": {"groups": [{"l0": "物流问题", "l1": "发货慢", "confidence": 0.9}],
                  "review_reasons": [], "translation_issues": [], "needs_human_review": False}},
        {"gold": {"gold_groups": [{"l0": "客服问题", "l1": "客服无人回复"}]},
         "pred": {"groups": [{"l0": "物流问题", "l1": "发货慢", "confidence": 0.4}],
                  "review_reasons": [], "translation_issues": [], "needs_human_review": False}},
    ]
    rc = risk_coverage(rows, TAX, thresholds=(0.0, 0.8, 0.9))
    assert len(rc) == 3
    assert rc[0]["coverage"] == 1.0
    assert rc[1]["coverage"] == 0.5
    assert rc[2]["coverage"] == 0.5
