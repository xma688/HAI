"""Load, persist, and update user profiles from JSON storage."""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from hai_avatar.schemas import UserProfile

logger = logging.getLogger(__name__)

_BIG_FIVE_KEYWORD_WEIGHTS = {
    "openness": {
        "interesting new curious explore different creative novel unique open-minded idea"
        " 有趣 新奇 探索 创造 创意 新颖 独特 开放 尝试": 0.06,
        "traditional routine familiar usual same"
        " 传统 习惯 熟悉 照旧 重复 不变": -0.04,
    },
    "conscientiousness": {
        "plan step organize careful detail prepared schedule arrange on time finish"
        " 计划 步骤 组织 仔细 细节 准备 安排 按时 完成": 0.04,
        "spontaneous random casual whatever lazy procrastinate"
        " 随意 随便 懒 拖延 不想 随便吧": -0.04,
    },
    "extraversion": {
        "talk share chat together friend meet group social party"
        " 聊天 分享 一起 朋友 见面 社交 聚会 热闹": 0.04,
        "alone quiet think reflect by myself solitary private"
        " 独处 安静 一个人 自己 私下 思考": -0.04,
    },
    "agreeableness": {
        "thank sorry please kind help cooperate agree together support nice"
        " 谢谢 对不起 请 帮助 合作 同意 支持 好的 不错": 0.04,
        "no don't won't refuse disagree argue bad wrong"
        " 不 不要 拒绝 不同意 争论 不好 错": -0.04,
    },
    "neuroticism": {
        "worry anxious stress nervous fear panic afraid upset overwhelmed insecure"
        " 担心 焦虑 紧张 害怕 恐慌 不安 难过 压力 疲 累": 0.05,
        "calm relaxed fine okay no problem easy handle"
        " 平静 放松 没事 没问题 简单 容易": -0.03,
    },
}


class ProfileManager:
    def __init__(self, profile_dir: Path, learning_rate: float = 0.05, affinity_decay: float = 0.95) -> None:
        self._profile_dir = profile_dir
        self._learning_rate = learning_rate
        self._affinity_decay = affinity_decay
        self._profile_dir.mkdir(parents=True, exist_ok=True)

    def get_or_create(self, user_id: str) -> UserProfile:
        path = self._profile_path(user_id)
        if path.exists():
            profile = UserProfile.model_validate(json.loads(path.read_text(encoding="utf-8")))
            logger.info("Loaded profile for user=%s interactions=%s", user_id, profile.interaction_count)
            return profile
        profile = UserProfile(user_id=user_id)
        self._save(profile)
        logger.info("Created new profile for user=%s", user_id)
        return profile

    def update(
        self,
        profile: UserProfile,
        user_text: str,
        emotions_used: list[str],
        gestures_used: list[str],
    ) -> UserProfile:
        profile.interaction_count += 1
        profile.updated_at = datetime.now(timezone.utc)

        self._update_big_five_from_text(profile, user_text)
        self._update_preferences_from_accumulated(profile)

        self._save(profile)
        logger.debug("Updated profile user=%s count=%s", profile.user_id, profile.interaction_count)
        return profile

    def set_self_report(self, profile: UserProfile, big_five_values: dict[str, float]) -> UserProfile:
        for dim in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
            if dim in big_five_values:
                setattr(profile.big_five, dim, max(0.0, min(1.0, big_five_values[dim])))
        profile.big_five.source = "self_report"
        self._save(profile)
        logger.info("Self-report Big Five set for user=%s", profile.user_id)
        return profile

    def delete(self, user_id: str) -> None:
        path = self._profile_path(user_id)
        if path.exists():
            path.unlink()
            logger.info("Deleted profile for user=%s", user_id)

    def _profile_path(self, user_id: str) -> Path:
        if re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", user_id) and user_id not in {".", ".."}:
            filename = user_id
        else:
            digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]
            filename = f"session-{digest}"
        return self._profile_dir / f"{filename}.json"

    def record_gesture_feedback(
        self,
        profile: UserProfile,
        gestures: list[str],
        liked: bool,
    ) -> UserProfile:
        """Update gesture affinity only from explicit user feedback."""

        delta = 0.08 if liked else -0.12
        for gesture in gestures:
            if gesture == "idle":
                continue
            current = profile.gesture_affinity.get(gesture, 0.5)
            profile.gesture_affinity[gesture] = round(max(0.0, min(1.0, current + delta)), 3)
        self._save(profile)
        return profile

    def _save(self, profile: UserProfile) -> None:
        self._profile_path(profile.user_id).write_text(
            json.dumps(profile.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _update_big_five_from_text(self, profile: UserProfile, text: str) -> None:
        lowered = text.lower()
        for dim, keyword_map in _BIG_FIVE_KEYWORD_WEIGHTS.items():
            delta = 0.0
            for keywords_str, weight in keyword_map.items():
                for kw in keywords_str.split():
                    if kw in lowered:
                        delta += weight
            if delta != 0:
                current = getattr(profile.big_five, dim)
                new_val = max(0.0, min(1.0, current + delta * self._learning_rate))
                setattr(profile.big_five, dim, round(new_val, 4))
                if profile.big_five.source == "default":
                    profile.big_five.source = "inferred"

    def _update_gesture_affinity(self, profile: UserProfile, gestures_used: list[str]) -> None:
        for g in gestures_used:
            if g == "idle":
                continue
            profile.gesture_affinity[g] = max(0.05, profile.gesture_affinity.get(g, 0.7) + 0.02)
        for key in list(profile.gesture_affinity.keys()):
            if key not in gestures_used:
                profile.gesture_affinity[key] *= self._affinity_decay
                if profile.gesture_affinity[key] < 0.05:
                    del profile.gesture_affinity[key]

    def _update_preferences_from_accumulated(self, profile: UserProfile) -> None:
        if profile.interaction_count < 5:
            return
        bf = profile.big_five
        prefs = profile.preferences

        if bf.source in ("inferred", "self_report"):
            if bf.neuroticism > 0.6:
                prefs.expressiveness_tolerance = round(max(0.3, prefs.expressiveness_tolerance - 0.05), 3)
            if bf.agreeableness > 0.7:
                prefs.expressiveness_tolerance = round(min(1.0, prefs.expressiveness_tolerance + 0.03), 3)
            if bf.extraversion < 0.35:
                prefs.gesture_frequency = "minimal"
            elif bf.extraversion > 0.7:
                prefs.gesture_frequency = "frequent"
            if bf.openness > 0.7:
                prefs.formality = "casual"
            elif bf.conscientiousness > 0.75:
                prefs.formality = "formal"
            if bf.neuroticism > 0.6:
                prefs.pace = "slow"
