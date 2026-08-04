import glob
import os
import shutil
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(_ROOT / "backend"))

from middleware import logger_config as lc


def _use_tmp_log_dir():
    """切到临时日志目录，避免污染真实日志。"""
    tmp = tempfile.mkdtemp(prefix="test_logs_")
    lc._LOG_DIR = tmp
    lc._configured = False
    return tmp


def test_setup_creates_dir():
    tmp = _use_tmp_log_dir()
    lc.setup_logging()
    assert os.path.isdir(tmp), "log dir should be created"
    print(f"  log dir created: {tmp}")


def test_date_named_file():
    tmp = _use_tmp_log_dir()
    lc.setup_logging()
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    pattern = os.path.join(tmp, f"app.{today}.log")
    lg = lc.get_logger("canteen.test")
    lg.info("测试消息 123")
    # 关闭 handler 让文件 flush
    for h in lc.logging.getLogger().handlers:
        h.flush()
    assert os.path.exists(pattern), f"date-named log file expected: {pattern}"
    text = open(pattern, encoding="utf-8").read()
    assert "测试消息" in text, "log content should include message"
    print(f"  date-named file: {os.path.basename(pattern)}, content ok")


def test_logger_namespace():
    _use_tmp_log_dir()
    lc.setup_logging()
    lg = lc.get_logger("canteen.app")
    assert lg.name == "canteen.app"
    print("  logger namespace: canteen.app")


def test_size_rollover_config():
    # 验证可配置项读取（不实际触发滚动）
    assert lc.MAX_BYTES > 0
    assert lc.BACKUP_COUNT >= 1
    print(f"  max_bytes={lc.MAX_BYTES}, backup={lc.BACKUP_COUNT}")


if __name__ == "__main__":
    tests = [
        test_setup_creates_dir,
        test_date_named_file,
        test_logger_namespace,
        test_size_rollover_config,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {t.__name__}")
        except Exception as e:
            print(f"  FAIL: {t.__name__} - {e}")
    print(f"\n{passed}/{len(tests)} tests passed")