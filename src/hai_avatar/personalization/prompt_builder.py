"""Generate personalized system prompt injection from user profile."""

from hai_avatar.schemas import BigFiveTraits, CommunicationPreferences, UserProfile


def build_personalized_system_prompt(profile: UserProfile) -> str:
    lines: list[str] = []

    bf = profile.big_five
    prefs = profile.preferences
    has_inferred = bf.source in ("inferred", "self_report")

    if has_inferred:
        lines.append(f"当前用户的 Big Five 人格特征参考: "
                     f"开放性 {bf.openness:.2f}, 尽责性 {bf.conscientiousness:.2f}, "
                     f"外向性 {bf.extraversion:.2f}, 宜人性 {bf.agreeableness:.2f}, "
                     f"神经质 {bf.neuroticism:.2f}。")

    _append_expressiveness_guidance(lines, bf, prefs, has_inferred)
    _append_formality_guidance(lines, prefs)
    _append_pace_guidance(lines, prefs)
    _append_gesture_affinity_guidance(lines, profile)
    _append_emotional_tone_guidance(lines, bf, has_inferred)

    lines.append("请在上述画像约束下生成最合适的回复。")
    return "\n".join(lines)


def _append_expressiveness_guidance(
    lines: list[str],
    bf: BigFiveTraits,
    prefs: CommunicationPreferences,
    has_inferred: bool,
) -> None:
    tol = prefs.expressiveness_tolerance
    if tol < 0.35:
        lines.append("该用户对夸张的表情动作接受度较低, 请优先使用 neutral 或 soft_smile 表情, 动作幅度偏内敛。")
    elif tol > 0.8:
        lines.append("该用户对丰富的表情动作接受度较高, 可以适当使用 smile、surprised 等表情来增强表达。")

    if has_inferred:
        if bf.openness > 0.7:
            lines.append("用户开放性较高, 可以尝试使用更丰富的表达方式和新颖的措辞。")
        if bf.neuroticism > 0.7:
            lines.append("用户神经质偏高, 回复中应更多使用 supportive 和 calm 的情绪风格, 避免 surprised 或 serious。")


def _append_formality_guidance(lines: list[str], prefs: CommunicationPreferences) -> None:
    guidance = {
        "casual": "用户偏好随意轻松的交流风格, 可使用更口语化、更亲切的表达方式。",
        "neutral": None,
        "formal": "用户偏好正式严肃的交流风格, 请使用规范的表达方式, 控制语气保持礼貌。",
    }
    g = guidance.get(prefs.formality)
    if g:
        lines.append(g)


def _append_pace_guidance(lines: list[str], prefs: CommunicationPreferences) -> None:
    guidance = {
        "slow": "用户偏好较慢的节奏, 回复应更简洁、停顿更长。",
        "moderate": None,
        "fast": "用户偏好较快的节奏, 回复应尽量简洁高效。",
    }
    g = guidance.get(prefs.pace)
    if g:
        lines.append(g)


def _append_gesture_affinity_guidance(lines: list[str], profile: UserProfile) -> None:
    if not profile.gesture_affinity:
        return
    high = [k for k, v in profile.gesture_affinity.items() if v > 0.7 and k != "idle"]
    low = [k for k, v in profile.gesture_affinity.items() if v < 0.25 and k != "idle"]
    if high:
        names = "、".join(high)
        lines.append(f"用户对以下动作反应良好, 可以适当增加: {names}。")
    if low:
        names = "、".join(low)
        lines.append(f"用户对以下动作反应不佳, 请尽量避免: {names}。")


def _append_emotional_tone_guidance(
    lines: list[str],
    bf: BigFiveTraits,
    has_inferred: bool,
) -> None:
    if not has_inferred:
        return
    if bf.agreeableness > 0.7:
        lines.append("用户宜人性较高, 可以使用温和、鼓励的语气。")
    if bf.extraversion < 0.3:
        lines.append("用户内向性较高, 避免过于热情或直接的表达, 给对方留出舒适空间。")
    if bf.conscientiousness > 0.7:
        lines.append("用户尽责性较高, 回复可以更有条理、分步骤呈现。")
