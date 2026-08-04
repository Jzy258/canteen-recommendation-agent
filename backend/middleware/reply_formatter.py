"""回复格式清理（B 拥有）

LLM 可能偶尔仍输出 Markdown 痕迹（**加粗**、`代码`、- 列表、| 表格）。
本模块在返回前做一次轻量清理，保证回复为纯文本自然语言。
"""
import re


def clean_markdown(text: str) -> str:
    """去除常见 Markdown 语法痕迹，保留纯文本。"""
    if not text:
        return text

    # 去除行首列表符号（- * + 数字.）
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+\.\s+", "", text)
    # 去除 Markdown 表格行（含 | 分隔）
    text = re.sub(r"(?m)^\s*\|.*\|\s*$", "", text)
    # 去除行首标题符号
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    # 行内代码与加粗
    text = text.replace("**", "")
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # 内联链接 [文本](url) -> 文本
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # 图片 ![alt](url) -> alt
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)

    # 清理多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()