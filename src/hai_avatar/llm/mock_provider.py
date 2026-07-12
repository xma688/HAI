"""Rule-based mock LLM provider for full pipeline testing."""

import json
import re

from hai_avatar.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Return varied structured responses without any API key."""

    async def generate(self, user_text: str) -> str:
        text = user_text.strip()
        scenario = self._detect_scenario(text)
        response = self._response_for(scenario)
        return json.dumps(response, ensure_ascii=False)

    def _detect_scenario(self, text: str) -> str:
        if re.search(r"你好|您好|hello|hi", text, re.IGNORECASE):
            return "greeting"
        if re.search(r"再见|拜拜|下次见|回头见", text):
            return "farewell"
        if re.search(r"对不起|抱歉|不好意思|说错", text):
            return "apology"
        if re.search(r"惊讶|惊喜|意外|令人惊讶", text):
            return "surprise"
        if re.search(r"压力|焦虑|不知道怎么开始|难受|担心", text):
            return "supportive"
        if re.search(r"不明白|解释|概念|为什么|怎么", text):
            return "explanation"
        if re.search(r"困惑| confused |疑惑", text, re.IGNORECASE):
            return "confusion"
        return "fallback"

    def _response_for(self, scenario: str) -> dict[str, object]:
        responses = {
            "greeting": {
                "reply_text": "你好，很高兴见到你。我们可以从一个小目标开始。",
                "emotion": "happy",
                "expression": "smile",
                "gestures": ["wave", "nod"],
                "voice_style": "cheerful",
                "pause_before_speech_ms": 100,
            },
            "supportive": {
                "reply_text": "没关系，我们先把任务拆成几个小步骤，一步一步推进。",
                "emotion": "supportive",
                "expression": "soft_smile",
                "gestures": ["nod", "explain"],
                "voice_style": "calm",
                "pause_before_speech_ms": 200,
            },
            "explanation": {
                "reply_text": "可以。我们先抓住核心概念，再用一个具体例子来验证理解。",
                "emotion": "thoughtful",
                "expression": "thinking",
                "gestures": ["think", "explain"],
                "voice_style": "gentle",
                "pause_before_speech_ms": 150,
            },
            "confusion": {
                "reply_text": "我理解这里有些不清楚。你可以指出最困惑的一点，我们先解决它。",
                "emotion": "confused",
                "expression": "confused",
                "gestures": ["head_tilt"],
                "voice_style": "calm",
                "pause_before_speech_ms": 150,
            },
            "farewell": {
                "reply_text": "好的，今天先到这里。需要时随时回来继续。",
                "emotion": "happy",
                "expression": "soft_smile",
                "gestures": ["wave"],
                "voice_style": "gentle",
                "pause_before_speech_ms": 100,
            },
            "apology": {
                "reply_text": "没关系，表达有偏差很正常。我们可以重新整理一下。",
                "emotion": "apologetic",
                "expression": "concerned",
                "gestures": ["small_bow", "nod"],
                "voice_style": "apologetic",
                "pause_before_speech_ms": 200,
            },
            "surprise": {
                "reply_text": "这确实有些出乎意料。我们可以先确认原因，再决定下一步。",
                "emotion": "surprised",
                "expression": "surprised",
                "gestures": ["head_tilt"],
                "voice_style": "neutral",
                "pause_before_speech_ms": 100,
            },
            "fallback": {
                "reply_text": "我明白了。我们可以先明确目标，再选择最合适的下一步。",
                "emotion": "neutral",
                "expression": "neutral",
                "gestures": ["idle"],
                "voice_style": "neutral",
                "pause_before_speech_ms": 0,
            },
        }
        return responses[scenario]
