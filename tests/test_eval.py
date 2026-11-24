# -*- coding: utf-8 -*-
import os

from voc_label_agent.eval import evaluate, pair_set
from voc_label_agent.taxonomy import Taxonomy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAX = Taxonomy(os.path.join(ROOT, "data", "taxonomy.json"))


def test_pair_set_canonicalizes():
    assert pair_set([{"l0": "物流问题", "l1": "物流状态无法跟踪"}], TAX) == frozenset({("物流问题", "物流状态无法跟踪/感知")})


def test_eval_basic_metrics():
    gold = [
        {"id": "1", "site": "US", "star": 1, "review_type": "差评",
         "gold_groups": [{"l0": "物流问题", "l1": "发货慢"}]},
        {"id": "2", "site": "US", "star": 5, "review_type": "好评",
         "gold_groups": [{"l0": "好评", "l1": "好评"}]},
        {"id": "3", "site": "EU", "star": 1, "review_type": "差评",
         "gold_groups": [{"l0": "客服问题", "l1": "客服无人回复"}]},
    ]
    preds = [
        {"id": "1", "prediction": {"review_type": "差评", "groups": [{"l0": "物流问题", "l1": "发货慢"}], "needs_human_review": False, "review_reasons": []}},
        {"id": "2", "prediction": {"review_type": "好评", "groups": [{"l0": "好评", "l1": "好评"}], "needs_human_review": False, "review_reasons": []}},
        {"id": "3", "prediction": {"review_type": "差评", "groups": [{"l0": "物流问题", "l1": "未收到包裹"}], "needs_human_review": True, "review_reasons": ["low_confidence"]}},
    ]
    m = evaluate(gold, preds, TAX)
    assert m["n"] == 3
    assert m["exact_set_match"] == 0.6667
    assert m["review_type_accuracy"] == 1.0
    assert m["error_capture_rate"] == 1.0
    assert m["tp"] == 2 and m["fp"] == 1 and m["fn"] == 1
