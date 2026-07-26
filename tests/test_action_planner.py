from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.schemas import EmotionType, ExpressionType, GestureType, LLMAvatarResponse


def test_unknown_emotion_downgrades_to_neutral():
    planner = ActionPlanner(enable_cooldown=False)
    command, warnings = planner.plan(
        LLMAvatarResponse(
            reply_text="x",
            emotion="unknown",
            expression="neutral",
            gestures=["idle"],
            voice_style="neutral",
        )
    )
    assert command.emotion == EmotionType.neutral
    assert warnings


def test_unknown_gesture_downgrades_to_idle():
    planner = ActionPlanner(enable_cooldown=False)
    command, _ = planner.plan(
        LLMAvatarResponse(
            reply_text="x",
            emotion="neutral",
            expression="neutral",
            gestures=["dance"],
            voice_style="neutral",
        )
    )
    assert command.gestures == [GestureType.idle]


def test_gestures_are_truncated():
    planner = ActionPlanner(max_gestures=2, enable_cooldown=False)
    command, warnings = planner.plan(
        LLMAvatarResponse(
            reply_text="x",
            emotion="happy",
            expression="smile",
            gestures=["wave", "nod", "explain"],
            voice_style="neutral",
        )
    )
    assert len(command.gestures) == 2
    assert any("truncated" in warning for warning in warnings)


def test_conflict_labels_are_corrected():
    planner = ActionPlanner(enable_cooldown=False)
    command, warnings = planner.plan(
        LLMAvatarResponse(
            reply_text="x",
            emotion="serious",
            expression="smile",
            gestures=["idle"],
            voice_style="serious",
        )
    )
    assert command.expression == ExpressionType.serious
    assert warnings


def test_distress_input_never_uses_smiling_expression():
    planner = ActionPlanner(enable_cooldown=False)
    command, _ = planner.plan(
        LLMAvatarResponse(
            reply_text="我在这里陪着你。",
            emotion="supportive",
            expression="soft_smile",
            gestures=["nod"],
            voice_style="calm",
        ),
        user_text="我真的很难过，也有点焦虑。",
    )
    assert command.expression == ExpressionType.concerned


def test_gesture_cooldown_replaces_repeated_gesture():
    planner = ActionPlanner(enable_cooldown=True)
    first, _ = planner.plan(
        LLMAvatarResponse(
            reply_text="x",
            emotion="happy",
            expression="smile",
            gestures=["wave"],
            voice_style="neutral",
        )
    )
    second, warnings = planner.plan(
        LLMAvatarResponse(
            reply_text="x",
            emotion="happy",
            expression="smile",
            gestures=["wave"],
            voice_style="neutral",
        )
    )
    assert first.gestures == [GestureType.wave]
    assert second.gestures != [GestureType.wave]
    assert warnings


def test_gesture_cooldown_is_isolated_by_context():
    planner = ActionPlanner(enable_cooldown=True)
    response = LLMAvatarResponse(
        reply_text="x",
        emotion="happy",
        expression="smile",
        gestures=["wave"],
        voice_style="neutral",
    )
    first, _ = planner.plan(response, context_id="session-a")
    other_session, warnings = planner.plan(response, context_id="session-b")

    assert first.gestures == [GestureType.wave]
    assert other_session.gestures == [GestureType.wave]
    assert warnings == []
