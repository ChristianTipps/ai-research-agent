from ai_research_agent.formatting import prepare_final_report
from ai_research_agent.notion import _markdown_blocks, clean_notion_title
from ai_research_agent.schemas import SourceRecord


def test_prepare_final_report_moves_links_to_sources_section() -> None:
    markdown = """# 1. Simple explanation

OpenAI tracing is useful ([OpenAI tracing](https://openai.github.io/openai-agents-python/tracing/?utm_source=openai)).
It should not show inline source domains (openai.github.io).

# 10. Sources and confidence
- Old source list should be rebuilt.
"""
    report = prepare_final_report(
        markdown,
        [
            SourceRecord(
                id="src_test",
                title="OpenAI tracing",
                url="https://openai.github.io/openai-agents-python/tracing/?utm_source=openai",
                confidence="high",
            )
        ],
    )

    body, sources = report.split("# 10. Sources and confidence")
    assert "https://" not in body
    assert "(openai.github.io)" not in body
    assert "**" not in body
    assert "[OpenAI tracing](https://openai.github.io/openai-agents-python/tracing/)" in sources
    assert "utm_source" not in sources


def test_markdown_blocks_preserve_bold_as_notion_annotation() -> None:
    blocks = _markdown_blocks("# Heading\n\n- **Bold** item")

    assert blocks[0]["type"] == "heading_1"
    list_item = blocks[1]["bulleted_list_item"]["rich_text"]
    assert list_item[0]["annotations"]["bold"] is True
    assert list_item[0]["text"]["content"] == "Bold"


def test_notion_title_removes_run_ids() -> None:
    assert clean_notion_title("Response: ", "Beginner Guide - run_abc123") == "Response: Beginner Guide"


def test_notion_blocks_clean_repeated_numbering() -> None:
    blocks = _markdown_blocks("1. 1. 1. First point")

    assert blocks[0]["type"] == "numbered_list_item"
    text = blocks[0]["numbered_list_item"]["rich_text"][0]["text"]["content"]
    assert text == "First point"


def test_notion_blocks_plainify_non_code_fences() -> None:
    blocks = _markdown_blocks("```text\nUser goal\n↓\nTool result\n```")

    assert blocks[0]["type"] == "paragraph"
