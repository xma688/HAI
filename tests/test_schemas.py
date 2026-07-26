from hai_avatar.planner.validator import parse_llm_avatar_response
from hai_avatar.schemas import EmotionType, LLMAvatarResponse


def test_plain_text_llm_output_is_accepted():
    parsed = parse_llm_avatar_response("hello")
    assert parsed.reply_text == "hello"
    assert parsed.emotion == "neutral"


def test_json_scalar_llm_output_is_accepted():
    parsed = parse_llm_avatar_response("5")
    assert parsed.reply_text == "5"
    assert parsed.expression == "neutral"


def test_valid_llm_json_parses():
    parsed = parse_llm_avatar_response(
        '{"reply_text":"你好","emotion":"happy","expression":"smile","gestures":["wave"],"voice_style":"cheerful"}'
    )
    assert isinstance(parsed, LLMAvatarResponse)
    assert parsed.emotion == EmotionType.happy.value


def test_markdown_wrapped_json_can_be_repaired():
    parsed = parse_llm_avatar_response(
        '```json\n{"reply_text":"你好","emotion":"happy","expression":"smile","gestures":["wave"],"voice_style":"cheerful"}\n```'
    )
    assert parsed.reply_text == "你好"
