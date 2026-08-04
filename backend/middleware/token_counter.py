"""Token 计数（B 拥有）

优先用 tiktoken（cl100k_base，OpenAI 通用 BPE），失败回退字符估算。
统一入口 count_tokens(text) / count_messages(messages)。
"""
from middleware.logger_config import get_logger

logger = get_logger("canteen.tokens")

_encoder = None
_use_fallback = False


def _get_encoder():
    """懒加载 tiktoken 编码器；失败则置 fallback 标志。"""
    global _encoder, _use_fallback
    if _use_fallback:
        return None
    if _encoder is None:
        try:
            import tiktoken
            _encoder = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning("tiktoken unavailable, fallback to char count: %s", e)
            _encoder = None
            _use_fallback = True
    return _encoder


def count_tokens(text: str) -> int:
    """统计单段文本 token 数。tiktoken 不可用时按字符估算（中文字符≈1 token）。"""
    if not text:
        return 0
    enc = _get_encoder()
    if enc is not None:
        try:
            return len(enc.encode(str(text)))
        except Exception:
            pass
    # 回退：中文按字，英文按 4 字符
    return sum(1 for ch in str(text) if ord(ch) > 127) + len(str(text)) // 4


def count_messages(messages: list) -> int:
    """统计消息列表 token 数（LangChain Message 或含 content 的对象）。"""
    total = 0
    for m in messages:
        content = getattr(m, "content", m) if not isinstance(m, str) else m
        total += count_tokens(content)
    return total