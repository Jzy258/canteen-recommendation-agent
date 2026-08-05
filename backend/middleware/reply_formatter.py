"""回复格式清理（B 拥有）

LLM 可能偶尔仍输出 Markdown 痕迹（**加粗**、`代码`、- 列表、| 表格）。
本模块在返回前做一次轻量清理，保证回复为纯文本自然语言。

- `clean_markdown`：非流式最终文本整体清理。
- `StreamMarkdownCleaner`：流式场景逐 chunk 状态化清理，跨 chunk 识别
  被拆分的 Markdown 标记（如 `**` 被切成 `*`+`*`），保证前端实时收到的
  增量已是纯文本。
"""
import re


def _clean_core(text: str) -> str:
    """清理核心（不做 strip / 空行合并，供流式分段使用）。"""
    # 去除行首列表符号（- * + 数字.）
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+\.\s+", "", text)
    # 去除 Markdown 表格行（含 | 分隔）
    text = re.sub(r"(?m)^\s*\|.*\|\s*$", "", text)
    # 去除引用与分隔线
    text = re.sub(r"(?m)^\s*>\s*", "", text)
    text = re.sub(r"(?m)^\s*(?:-{3,}|_{3,}|\*{3,})\s*$", "", text)
    # 去除行首标题符号
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    # 行内代码与加粗
    text = text.replace("**", "")
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # 内联链接 [文本](url) -> 文本
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # 图片 ![alt](url) -> alt
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # 删除表格分隔符（避免表格行被截断时残留 |）
    text = text.replace("|", "")
    # 删除不成对的行内单星号（*斜体* -> 斜体）
    text = re.sub(r"(?<!\*)\*(?!\*)", "", text)
    return text


def clean_markdown(text: str) -> str:
    """去除常见 Markdown 语法痕迹，保留纯文本。"""
    if not text:
        return text
    text = _clean_core(text)
    # 清理多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class StreamMarkdownCleaner:
    """流式 Markdown 清理器：状态机逐字符识别并剥离标记。

    用法：
        cleaner = StreamMarkdownCleaner()
        for chunk in stream:
            out = cleaner.push(chunk)   # 返回可立即推送的纯文本增量
            if out:
                yield out
        reply = cleaner.flush()         # 返回尾部剩余（含 buffer 收尾）

    设计：
    - 用状态机而非「切段 + 正则」：加粗 `` ** ``、行内代码 `` ` ``、
      行首列表/标题/引用/表格、内联链接 `` [x](url) `` 都按字符识别，
      跨 chunk 拆分（如 `` * `` 与 `` * `` 分属两个增量）也能正确衔接；
    - 需要前瞻但数据不足时（如行首 `` - `` 等下一字符确定是否为列表），
      先缓冲等待下一增量，保证不会把标记拆散或误判；
    - 无换行的长文本/短文本也不会被整体缓存，字符确定后即吐出，流式实时。
    """

    def __init__(self):
        self._buf = ""
        self._at_line_start = True
        self._in_bold = False
        self._in_code = False
        self._in_link_text = False
        self._in_link_url = False

    def push(self, chunk: str) -> str:
        if not chunk:
            return ""
        self._buf += chunk
        return self._drain(force=False)

    def flush(self) -> str:
        out = self._drain(force=True)
        out = re.sub(r"\n{3,}", "\n\n", out)
        return out.strip()

    def _drain(self, force: bool) -> str:
        parts = []
        while self._buf:
            ch = self._buf[0]
            nxt = self._buf[1] if len(self._buf) > 1 else None

            # --- 加粗 ** ---
            if ch == "*" and nxt == "*":
                self._in_bold = not self._in_bold
                self._buf = self._buf[2:]
                continue
            if ch == "*" and nxt is None and not force:
                break  # 跨 chunk 待定，等下一增量判断是否成对

            # --- 行内代码 ` ---
            if ch == "`":
                self._in_code = not self._in_code
                self._buf = self._buf[1:]
                continue

            # --- 内联链接 [x](url) ---
            if self._in_link_url:
                self._buf = self._buf[1:]
                if ch == ")":
                    self._in_link_url = False
                continue
            if ch == "[" and not self._in_bold and not self._in_code:
                self._in_link_text = True
                self._buf = self._buf[1:]
                continue
            if self._in_link_text:
                if ch == "]" and nxt == "(":
                    self._in_link_text = False
                    self._in_link_url = True
                    self._buf = self._buf[2:]
                    continue
                if ch == "]" and nxt is None and not force:
                    break  # 跨 chunk 待定，等待判断 `]` 后是否跟随 `(`
                if ch == "]":
                    self._in_link_text = False
                    self._buf = self._buf[1:]
                    continue
                parts.append(ch)
                self._buf = self._buf[1:]
                continue

            # --- 表格分隔符 |（纯文本无意义，全局删除）---
            if ch == "|":
                self._buf = self._buf[1:]
                continue

            # --- 行首标记：列表 / 标题 / 引用 ---
            if self._at_line_start and not self._in_bold and not self._in_code:
                if ch in "-*+" and nxt == " ":
                    self._buf = self._buf[2:]
                    continue
                if ch in "#>":
                    self._buf = self._buf[1:]
                    continue
                if ch.isdigit() and nxt == ".":
                    k = 0
                    while k < len(self._buf) and self._buf[k].isdigit():
                        k += 1
                    if (k + 1 < len(self._buf) and self._buf[k] == "."
                            and self._buf[k + 1] == " "):
                        self._buf = self._buf[k + 2:]
                        continue
<<<<<<< HEAD
=======
                # 行首待定：`-`/数字等可能是列表起始，但数据不足时
                # 无法确认后随字符（空格或换行），交给普通字符输出并恢复行首状态
>>>>>>> main
                if ch in "-*+" and nxt is None and not force:
                    break  # 跨 chunk 待定，等下一增量确认是否为列表符
                if ch.isdigit() and nxt is None and not force:
                    break

            # --- 普通字符 ---
            parts.append(ch)
            self._at_line_start = (ch == "\n")
            self._buf = self._buf[1:]
        return "".join(parts)
