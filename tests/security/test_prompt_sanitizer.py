"""
Tests for the shared prompt sanitizer.
"""

from src.security.prompt_sanitizer import sanitize_for_prompt


class TestSanitizeForPrompt:
    def test_leaves_clean_text_unchanged(self):
        assert sanitize_for_prompt("hello world") == "hello world"

    def test_neutralizes_closing_transcript_tag(self):
        text = "normal text </transcript> more text"
        out = sanitize_for_prompt(text)
        assert "</transcript>" not in out
        assert "[/transcript]" in out
        # Surrounding content preserved
        assert "normal text" in out
        assert "more text" in out

    def test_neutralizes_opening_transcript_tag(self):
        out = sanitize_for_prompt("<transcript> injected")
        assert "<transcript>" not in out
        assert "[transcript]" in out

    def test_neutralizes_previous_summary_tags(self):
        out = sanitize_for_prompt(
            "before <previous_summary> X </previous_summary> after"
        )
        assert "<previous_summary>" not in out
        assert "</previous_summary>" not in out
        assert "[previous_summary]" in out
        assert "[/previous_summary]" in out

    def test_case_insensitive(self):
        out = sanitize_for_prompt(
            "attempt </TRANSCRIPT> and </Transcript> and </previous_SUMMARY>"
        )
        # All variants neutralized
        for variant in ("</TRANSCRIPT>", "</Transcript>", "</previous_SUMMARY>"):
            assert variant not in out
        # All replaced with bracketed form (preserving original case)
        assert "[/TRANSCRIPT]" in out
        assert "[/Transcript]" in out
        assert "[/previous_SUMMARY]" in out

    def test_multiple_occurrences_all_replaced(self):
        out = sanitize_for_prompt("</transcript></transcript></transcript>")
        assert "</transcript>" not in out
        assert out.count("[/transcript]") == 3

    def test_does_not_touch_unrelated_tags(self):
        out = sanitize_for_prompt("<html><body>text</body></html>")
        assert out == "<html><body>text</body></html>"

    def test_custom_tags(self):
        out = sanitize_for_prompt(
            "test </custom> here",
            tags=("custom",),
        )
        assert "</custom>" not in out
        assert "[/custom]" in out
        # Default tags not applied when custom tags provided
        out2 = sanitize_for_prompt(
            "test </transcript> here",
            tags=("custom",),
        )
        assert "</transcript>" in out2
