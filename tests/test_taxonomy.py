# -*- coding: utf-8 -*-
import os

from voc_label_agent.taxonomy import Taxonomy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_loads_and_aliases():
    tax = Taxonomy(os.path.join(ROOT, "data", "taxonomy.json"))
    assert "物流问题" in tax.groups
    assert tax.canonical("蓝牙功能差") == "APP连接问题"
    assert tax.l0_for("配件损坏") == "产品问题"
    assert tax.is_valid_pair("客服问题", "客服无人回复")
    assert not tax.is_valid_pair("物流问题", "客服无人回复")


def test_prompt_block_has_no_alias_duplicates():
    tax = Taxonomy(os.path.join(ROOT, "data", "taxonomy.json"))
    block = tax.prompt_block()
    assert "蓝牙功能差" not in block
    assert "配件损坏" not in block
