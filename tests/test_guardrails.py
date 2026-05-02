"""Tests for input/output guardrails."""

from src.guardrails import validate_input, validate_output


class TestValidateInput:
    """Tests for input validation."""

    def test_valid_question(self):
        result = validate_input("How many PTO days do I get?")
        assert result["valid"] is True
        assert result["error"] is None

    def test_empty_question(self):
        result = validate_input("")
        assert result["valid"] is False
        assert "enter a question" in result["error"].lower()

    def test_none_question(self):
        result = validate_input(None)
        assert result["valid"] is False

    def test_whitespace_only(self):
        result = validate_input("   ")
        assert result["valid"] is False

    def test_too_short(self):
        result = validate_input("hi")
        assert result["valid"] is False
        assert "too short" in result["error"].lower()

    def test_too_long(self):
        result = validate_input("a" * 501)
        assert result["valid"] is False
        assert "too long" in result["error"].lower()

    def test_off_topic_code(self):
        result = validate_input("Write me a Python code script")
        assert result["valid"] is False
        assert "only answer questions" in result["error"].lower()

    def test_off_topic_weather(self):
        result = validate_input("What is the weather today?")
        assert result["valid"] is False

    def test_off_topic_recipe(self):
        result = validate_input("Give me a recipe for cookies")
        assert result["valid"] is False

    def test_on_topic_pto(self):
        result = validate_input("What is the PTO carryover limit?")
        assert result["valid"] is True

    def test_on_topic_security(self):
        result = validate_input("What are the password requirements?")
        assert result["valid"] is True


class TestValidateOutput:
    """Tests for output validation."""

    def test_normal_output_with_citation(self):
        answer = "According to [pto-and-leave-policy], you get 15 days."
        result = validate_output(answer)
        assert result == answer

    def test_empty_output(self):
        result = validate_output("")
        assert "try rephrasing" in result.lower()

    def test_none_output(self):
        result = validate_output(None)
        assert "try rephrasing" in result.lower()

    def test_output_without_citation_adds_note(self):
        answer = "You get 15 PTO days per year."
        result = validate_output(answer)
        assert "verify this information" in result.lower()

    def test_out_of_scope_no_note_added(self):
        answer = "I don't have enough information in our policy documents to answer that."
        result = validate_output(answer)
        assert "verify this information" not in result.lower()

    def test_very_long_output_truncated(self):
        answer = "x" * 5000
        result = validate_output(answer)
        assert len(result) <= 4200  # 4000 + buffer for truncation and appended note
