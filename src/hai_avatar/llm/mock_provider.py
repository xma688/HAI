"""Rule-based mock LLM provider for full pipeline testing."""

import json
import re

from hai_avatar.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Return varied structured responses without any API key."""

    async def generate(
        self,
        user_text: str,
        system_prompt: str = "",
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        text = user_text.strip()
        scenario = self._detect_scenario(text)
        response = self._response_for(scenario, system_prompt)
        response = self._avoid_recent_gestures(response, conversation_history)
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

    def _response_for(self, scenario: str, system_prompt: str = "") -> dict[str, object]:
        responses = {
            "greeting": {
                "reply_text": "你好，很高兴见到你。我们可以从一个小目标开始。",
                "emotion": "happy",
                "expression": "smile",
                "gestures": ["wave", "nod"],
                "voice_style": "cheerful",
                "gesture_intensity": 0.7,
                "speaking_rate": 1.1,
                "pause_before_speech_ms": 100,
            },
            "supportive": {
                "reply_text": "没关系，我们先把任务拆成几个小步骤，一步一步推进。",
                "emotion": "supportive",
                "expression": "soft_smile",
                "gestures": ["nod", "explain"],
                "voice_style": "calm",
                "gesture_intensity": 0.35,
                "speaking_rate": 0.8,
                "pause_before_speech_ms": 300,
            },
            "explanation": {
                "reply_text": "可以。我们先抓住核心概念，再用一个具体例子来验证理解。",
                "emotion": "thoughtful",
                "expression": "thinking",
                "gestures": ["think", "explain"],
                "voice_style": "gentle",
                "gesture_intensity": 0.45,
                "speaking_rate": 0.85,
                "pause_before_speech_ms": 200,
            },
            "confusion": {
                "reply_text": "我理解这里有些不清楚。你可以指出最困惑的一点，我们先解决它。",
                "emotion": "confused",
                "expression": "confused",
                "gestures": ["head_tilt"],
                "voice_style": "calm",
                "gesture_intensity": 0.35,
                "speaking_rate": 0.9,
                "pause_before_speech_ms": 200,
            },
            "farewell": {
                "reply_text": "好的，今天先到这里。需要时随时回来继续。",
                "emotion": "happy",
                "expression": "soft_smile",
                "gestures": ["wave"],
                "voice_style": "gentle",
                "gesture_intensity": 0.5,
                "speaking_rate": 1.0,
                "pause_before_speech_ms": 100,
            },
            "apology": {
                "reply_text": "没关系，表达有偏差很正常。我们可以重新整理一下。",
                "emotion": "apologetic",
                "expression": "concerned",
                "gestures": ["small_bow", "nod"],
                "voice_style": "apologetic",
                "gesture_intensity": 0.3,
                "speaking_rate": 0.9,
                "pause_before_speech_ms": 200,
            },
            "surprise": {
                "reply_text": "这确实有些出乎意料。我们可以先确认原因，再决定下一步。",
                "emotion": "surprised",
                "expression": "surprised",
                "gestures": ["head_tilt"],
                "voice_style": "neutral",
                "gesture_intensity": 0.6,
                "speaking_rate": 1.05,
                "pause_before_speech_ms": 150,
            },
            "fallback": {
                "reply_text": "我明白了。我们可以先明确目标，再选择最合适的下一步。",
                "emotion": "neutral",
                "expression": "neutral",
                "gestures": ["idle"],
                "voice_style": "neutral",
                "gesture_intensity": 0.3,
                "speaking_rate": 1.0,
                "pause_before_speech_ms": 0,
            },
        }
        response = responses[scenario]
        response = self._apply_prompt_modifiers(response, system_prompt)
        return response

    def _avoid_recent_gestures(
        self,
        response: dict[str, object],
        history: list[dict[str, str]] | None,
    ) -> dict[str, object]:
        if not history:
            return response
        recent_gestures: set[str] = set()
        for msg in history[-3:]:
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            for token in TokenExtractor.extract_gestures(content):
                recent_gestures.add(token)
        modified = dict(response)
        gestures = list(modified.get("gestures", []))
        if gestures and all(g in recent_gestures for g in gestures):
            modified["gestures"] = ["nod"]
        return modified

    def _apply_prompt_modifiers(self, response: dict[str, object], prompt: str) -> dict[str, object]:
        if not prompt:
            return response
        modified = dict(response)
        lowered = prompt.lower()

        if "低" in prompt and ("接受度" in prompt or "容忍度" in prompt) and "表情" in prompt:
            if modified.get("expression") not in ("neutral", "soft_smile"):
                modified["expression"] = "soft_smile"
            modified["gesture_intensity"] = min(float(modified.get("gesture_intensity", 0.5)), 0.35)

        if "surprised" in lowered and "避免" in lowered:
            if modified.get("emotion") == "surprised":
                modified["emotion"] = "neutral"
                modified["expression"] = "neutral"

        if ("calm" in lowered or "supportive" in lowered) and "优先" in lowered:
            if modified.get("voice_style") != "calm":
                modified["voice_style"] = "calm"

        if "正式" in prompt or "规范" in prompt:
            modified["voice_style"] = "neutral"

        if "简洁" in prompt and "回复" in prompt:
            if isinstance(modified.get("reply_text"), str):
                text = str(modified["reply_text"])
                if len(text) > 15:
                    modified["reply_text"] = text[:15] + "。"

        return modified


class TokenExtractor:
    GESTURE_TOKENS = {"wave", "nod", "head_tilt", "think", "explain", "agree", "small_bow", "idle"}

    @staticmethod
    def extract_gestures(content: str) -> list[str]:
        found: list[str] = []
        for token in TokenExtractor.GESTURE_TOKENS:
            if token in content:
                found.append(token)
        return found
