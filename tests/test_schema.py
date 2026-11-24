# -*- coding: utf-8 -*-
import os

from voc_label_agent.schema import postprocess
from voc_label_agent.taxonomy import Taxonomy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAX = Taxonomy(os.path.join(ROOT, "data", "taxonomy.json"))


def test_caps_at_two_groups():
    raw = {"groups": [
        {"l0": "物流问题", "l1": "发货慢", "evidence": "slow", "confidence": 0.9},
        {"l0": "客服问题", "l1": "客服响应慢", "evidence": "slow reply", "confidence": 0.8},
        {"l0": "产品问题", "l1": "产品噪音", "evidence": "noise", "confidence": 0.7},
    ]}
    out = postprocess(raw, 1, "slow slow reply noise", "slow", TAX)
    assert len(out["groups"]) == 2
    assert "multi_label_overflow" in out["review_reasons"]


def test_drops_unknown_label():
    raw = {"groups": [{"l0": "产品问题", "l1": "不存在标签", "evidence": "x", "confidence": 0.9}]}
    out = postprocess(raw, 1, "x", "x", TAX)
    assert "label_not_in_taxonomy" in out["review_reasons"]
    assert out["groups"][0]["l1"] == "无具体指向的差评"


def test_positive_is_forced_to_good():
    raw = {"review_type": "中评", "groups": [{"l0": "物流问题", "l1": "发货慢", "evidence": "slow", "confidence": 0.9}]}
    out = postprocess(raw, 5, "slow but great", "slow", TAX)
    assert out["review_type"] == "好评"
    assert out["groups"] == [{"l0": "好评", "l1": "好评", "evidence": "slow", "confidence": 0.95}]
    assert "star_type_conflict" in out["review_reasons"]
    assert "positive_forced_good" in out["review_reasons"]


def test_mid_without_issue_gets_generic_label():
    out = postprocess({"groups": []}, 3, "it is okay", "it is okay", TAX)
    assert out["groups"][0]["l0"] == "中评"
    assert out["groups"][0]["l1"] == "无具体指向的差评"


def test_evidence_must_be_verbatim():
    raw = {"groups": [{"l0": "物流问题", "l1": "发货慢", "evidence": "not in text", "confidence": 0.9}]}
    out = postprocess(raw, 1, "the package arrived late", "package late", TAX)
    assert "evidence_not_found" in out["review_reasons"]
    assert out["groups"][0]["confidence"] <= 0.5
