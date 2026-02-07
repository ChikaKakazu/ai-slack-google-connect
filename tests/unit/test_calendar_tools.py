"""Tests for calendar_tools module."""

from tools.calendar_tools import get_tool_definitions


class TestGetToolDefinitions:
    def test_returns_four_tools(self):
        tools = get_tool_definitions()
        assert len(tools) == 4

    def test_search_free_slots_tool(self):
        tools = get_tool_definitions()
        search_tool = next(t for t in tools if t["name"] == "search_free_slots")

        assert "input_schema" in search_tool
        required = search_tool["input_schema"]["required"]
        assert "attendees" in required
        assert "date" not in required  # date is optional, defaults to today

    def test_create_event_tool(self):
        tools = get_tool_definitions()
        create_tool = next(t for t in tools if t["name"] == "create_event")

        required = create_tool["input_schema"]["required"]
        assert "summary" in required
        assert "start_time" in required
        assert "end_time" in required
        assert "attendees" in required

    def test_reschedule_event_tool(self):
        tools = get_tool_definitions()
        reschedule_tool = next(t for t in tools if t["name"] == "reschedule_event")

        required = reschedule_tool["input_schema"]["required"]
        assert "event_id" in required
        assert "new_start_time" in required
        assert "new_end_time" in required

    def test_suggest_reschedule_tool(self):
        tools = get_tool_definitions()
        suggest_tool = next(t for t in tools if t["name"] == "suggest_reschedule")

        props = suggest_tool["input_schema"]["properties"]
        assert "event_id" in props
        assert "event_title" in props
        # Both event_id and event_title are optional (either one can be used)
        required = suggest_tool["input_schema"]["required"]
        assert "event_id" not in required
        assert "event_title" not in required

    def test_search_free_slots_has_summary_property(self):
        tools = get_tool_definitions()
        search_tool = next(t for t in tools if t["name"] == "search_free_slots")

        props = search_tool["input_schema"]["properties"]
        assert "summary" in props
        assert props["summary"]["type"] == "string"
        assert props["summary"]["default"] == "ミーティング"

    def test_all_tools_have_description(self):
        tools = get_tool_definitions()
        for tool in tools:
            assert "description" in tool
            assert len(tool["description"]) > 0
