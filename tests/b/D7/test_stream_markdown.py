import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from middleware.reply_formatter import clean_markdown, StreamMarkdownCleaner


def test_stream_bold_split_across_chunks():
    """** 被 LLM 切成 * + * 两个 chunk 时仍能正确清理。"""
    cleaner = StreamMarkdownCleaner()
    out = []
    for ch in "**红烧肉** 很合适":
        piece = cleaner.push(ch)
        if piece:
            out.append(piece)
    final = "".join(out) + cleaner.flush()
    assert "**" not in final
    assert "红烧肉" in final
    print(f"  bold split handled: {final!r}")


def test_stream_strips_all_markdown_marks():
    cleaner = StreamMarkdownCleaner()
    full = "## 推荐\n\n- 红烧肉\n- `500kcal`\n[链接](http://x)"
    out = []
    for ch in full:
        piece = cleaner.push(ch)
        if piece:
            out.append(piece)
    final = "".join(out) + cleaner.flush()
    assert "**" not in final and "`" not in final
    assert "##" not in final and "- " not in final
    assert "](http" not in final
    assert "红烧肉" in final and "500kcal" in final
    print(f"  full marks stripped: {final!r}")


def test_stream_keeps_plain_text():
    cleaner = StreamMarkdownCleaner()
    full = "今天食堂有红烧肉，很下饭。"
    out = []
    for ch in full:
        piece = cleaner.push(ch)
        if piece:
            out.append(piece)
    final = "".join(out) + cleaner.flush()
    assert "今天食堂有红烧肉" in final
    print(f"  plain kept: {final!r}")


def test_clean_table_and_quote():
    r = clean_markdown("| 菜名 | 价格 |\n|---|---|\n| 红烧肉 | 12 |")
    assert "|" not in r
    r2 = clean_markdown("> 注意：清淡优先")
    assert not r2.startswith(">")
    print(f"  table/quote stripped: {r!r} / {r2!r}")


def test_clean_single_asterisk_italic():
    r = clean_markdown("*清淡* 优先")
    assert "*" not in r
    assert "清淡" in r
    print(f"  italic stripped: {r!r}")


def test_clean_table_pipe_without_full_row():
    """表格行被截断残留的 | 也会被删掉。"""
    r = clean_markdown("红烧肉 | 12")
    assert "|" not in r
    print(f"  stray pipe stripped: {r!r}")


if __name__ == "__main__":
    tests = [
        test_stream_bold_split_across_chunks,
        test_stream_strips_all_markdown_marks,
        test_stream_keeps_plain_text,
        test_clean_table_and_quote,
        test_clean_single_asterisk_italic,
        test_clean_table_pipe_without_full_row,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {t.__name__} - {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
