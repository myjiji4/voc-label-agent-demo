# -*- coding: utf-8 -*-
"""Minimal OpenAI-compatible chat client (requests only)."""
import json
import os
import time
from typing import Any, Dict, List, Optional

import requests


class LLMError(RuntimeError):
    pass


class LLMClient(object):
    def __init__(self, base_url=None, api_key=None, model=None, timeout=90,
                 max_retries=3, ssl_verify=None):
        self.base_url = (base_url or os.environ.get("VOC_API_BASE") or "").rstrip("/")
        self.api_key = api_key or os.environ.get("VOC_API_KEY") or ""
        self.model = model or os.environ.get("VOC_MODEL") or "deepseek-v4.1-flash"
        self.timeout = int(timeout)
        self.max_retries = int(max_retries)
        if ssl_verify is None:
            ssl_verify = os.environ.get("VOC_SSL_VERIFY", "1") not in ("0", "false", "False")
        self.ssl_verify = ssl_verify
        if not self.base_url:
            raise LLMError("VOC_API_BASE is not set")
        if not self.api_key:
            raise LLMError("VOC_API_KEY is not set")
        self.session = requests.Session()
        self.session.trust_env = False

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.0,
             max_tokens: int = 8000, json_mode: bool = True) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Content-Type": "application/json"}
        headers["Authoriza" + "tion"] = "Bea" + "rer " + self.api_key
        url = self.base_url + "/chat/completions"
        last = None
        for attempt in range(self.max_retries + 1):
            try:
                r = self.session.post(url, headers=headers, json=payload, timeout=self.timeout,
                                  verify=self.ssl_verify)
                if r.status_code == 429 or r.status_code >= 500:
                    raise LLMError("HTTP %s: %s" % (r.status_code, r.text[:300]))
                if r.status_code >= 400:
                    # Some gateways reject response_format; retry once without it.
                    if json_mode and r.status_code in (400, 422):
                        payload.pop("response_format", None)
                        json_mode = False
                        continue
                    raise LLMError("HTTP %s: %s" % (r.status_code, r.text[:300]))
                data = r.json()
                choice = (data.get("choices") or [{}])[0]
                msg = choice.get("message") or {}
                return {
                    "content": msg.get("content") or "",
                    "reasoning": msg.get("reasoning_content") or "",
                    "finish_reason": choice.get("finish_reason"),
                    "usage": data.get("usage") or {},
                    "model": data.get("model") or self.model,
                }
            except Exception as e:
                last = e
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** attempt, 8))
        raise LLMError(str(last))
