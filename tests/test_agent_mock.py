# -*- coding: utf-8 -*-
from voc_label_agent.agent import LabelAgent
from voc_label_agent.taxonomy import Taxonomy
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeClient(object):
    def __init__(self, content):
        self.content = content
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        return {"content": self.content, "usage": {"total_tokens": 10}}


def test_agent_returns_structured_prediction():
    tax = Taxonomy(os.path.join(ROOT, "data", "taxonomy.json"))
    content = '{"review_type":"差评","facts_original":["late"],"facts_translated":["late"],"translation_issues":[],"groups":[{"l0":"物流问题","l1":"发货慢","evidence":"arrived late","confidence":0.9}],"needs_human_review":false,"review_reasons":[]}'
    agent = LabelAgent(tax, FakeClient(content))
    out = agent.label({"id": "x", "site": "US", "star": 1, "text_original": "arrived late", "text_translated": "late"})
    assert out["error"] is None
    assert out["prediction"]["groups"][0]["l1"] == "发货慢"
    assert out["prediction"]["needs_human_review"] is False
