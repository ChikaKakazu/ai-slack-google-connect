"""Tests for message_handler module."""

from handlers.message_handler import _clean_mention_text


class TestCleanMentionText:
    def test_removes_single_mention(self):
        assert _clean_mention_text("<@U12345> hello") == "hello"

    def test_removes_mention_with_extra_spaces(self):
        assert _clean_mention_text("<@U12345>   hello world") == "hello world"

    def test_no_mention(self):
        assert _clean_mention_text("hello") == "hello"

    def test_empty_after_mention(self):
        assert _clean_mention_text("<@U12345>") == ""

    def test_multiple_mentions(self):
        result = _clean_mention_text("<@U12345> <@U67890> meeting")
        assert result == "meeting"
