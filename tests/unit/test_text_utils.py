from app.utils.text_utils import clean_whitespace, sanitize_filename, truncate


def test_truncate_short_text():
    assert truncate("hello", 100) == "hello"


def test_truncate_long_text():
    text = "word " * 2000
    result = truncate(text, max_chars=100)
    assert len(result) <= 104  # a bit of slack for "..."
    assert result.endswith("...")


def test_clean_whitespace():
    assert clean_whitespace("hello   world") == "hello world"
    assert clean_whitespace("a\n\n\n\nb") == "a\n\nb"


def test_sanitize_filename():
    assert sanitize_filename('hello/world:foo"bar') == "hello_world_foo_bar"
    assert sanitize_filename("normal name") == "normal_name"
