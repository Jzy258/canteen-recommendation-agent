import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from middleware.reply_formatter import clean_markdown


def test_strip_bold_and_code():
    r = clean_markdown("**红烧肉** 很合适，`500kcal`，12元")
    assert "**" not in r and "`" not in r
    assert "红烧肉" in r and "500kcal" in r
    print(f"  bold/code stripped: {r!r}")


def test_strip_list_bullets():
    r = clean_markdown("- 红烧肉\n- 宫保鸡丁\n- 米饭")
    assert "- " not in r
    assert "红烧肉" in r and "宫保鸡丁" in r
    print(f"  bullets stripped: {r!r}")


def test_strip_header():
    r = clean_markdown("## 推荐\n\n**高蛋白** 优先")
    assert not r.startswith("##")
    print(f"  header stripped: {r!r}")


def test_strip_inline_link():
    r = clean_markdown("[红烧肉](http://x) 与 米饭")
    assert "](http" not in r
    assert "红烧肉" in r
    print(f"  link stripped: {r!r}")


def test_plain_text_unchanged():
    r = clean_markdown("今天食堂有红烧肉，很下饭。")
    assert "今天食堂有红烧肉" in r
    print(f"  plain kept: {r!r}")


if __name__ == "__main__":
    tests = [
        test_strip_bold_and_code,
        test_strip_list_bullets,
        test_strip_header,
        test_strip_inline_link,
        test_plain_text_unchanged,
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