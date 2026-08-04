"""统一日志系统（B 拥有）

- 日志统一存放：backend/logs/
- 滚动策略：日期 + 大小双维度
  - 按天滚动（每天一个新文件，保留 N 天）
  - 单文件超过大小上限也滚动（防止单日文件过大）
- 命名：app.YYYY-MM-DD.log（按天），超大小则 app.YYYY-MM-DD.1.log
- 提供 get_logger(name) 统一入口，供各模块复用
"""
import logging
import logging.handlers
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 日志目录（backend/logs）
_LOG_DIR = os.getenv("LOG_DIR", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "logs"))
_LOG_DIR = os.path.abspath(_LOG_DIR)

# 配置
MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "5_000_000"))  # 单文件 5MB
BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "7"))    # 保留 7 份（天/轮）
LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# 已初始化标志，避免重复配置
_configured = False


class DateSizeRotatingHandler(RotatingFileHandler):
    """按天 + 大小双重滚动的文件 Handler。

    每日零点或文件超大小上限时滚动：
    - 按天：文件名带日期（app.YYYY-MM-DD.log）
    - 按大小：超过 MAX_BYTES 时追加序号（app.YYYY-MM-DD.1.log）
    """

    def __init__(self, filename, mode="a", max_bytes=0, backup_count=0,
                 encoding="utf-8", delay=False, utc=False):
        self._orig_filename = filename
        self._utc = utc
        self._date_prefix = None
        self._update_dated_filename()
        super().__init__(
            self._current_filename, mode=mode,
            maxBytes=max_bytes, backupCount=backup_count,
            encoding=encoding, delay=delay,
        )

    def _today_str(self) -> str:
        t = datetime.utcnow() if self._utc else datetime.now()
        return t.strftime("%Y-%m-%d")

    def _update_dated_filename(self):
        """根据当前日期生成带日期的文件名。"""
        base, ext = os.path.splitext(self._orig_filename)
        self._date_prefix = self._today_str()
        self._current_filename = f"{base}.{self._date_prefix}{ext}"

    def shouldRollover(self, record) -> bool:
        # 日期变化时也要滚动
        if self._today_str() != self._date_prefix:
            return True
        return super().shouldRollover(record)

    def doRollover(self):
        # 若因日期变化触发，先更新带日期的文件名再重新打开
        if self._today_str() != self._date_prefix:
            self._update_dated_filename()
            self.baseFilename = os.path.abspath(self._current_filename)
            self.stream = self._open()
        else:
            super().doRollover()


def setup_logging() -> None:
    """初始化根日志配置（幂等）。"""
    global _configured
    if _configured:
        return

    os.makedirs(_LOG_DIR, exist_ok=True)
    log_file = os.path.join(_LOG_DIR, "app.log")

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = DateSizeRotatingHandler(
        filename=log_file,
        max_bytes=MAX_BYTES,
        backup_count=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(LEVEL)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(LEVEL)

    root = logging.getLogger()
    root.setLevel(LEVEL)
    root.addHandler(file_handler)
    root.addHandler(console)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """获取统一配置的 logger（未初始化时自动初始化）。"""
    setup_logging()
    return logging.getLogger(name)


# 模块导入时确保目录存在（但不强制配置，避免测试副作用）
os.makedirs(_LOG_DIR, exist_ok=True)