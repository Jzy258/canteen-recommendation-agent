"""项目版本管理（单一事实来源 · SemVer）

遵循 https://semver.org/lang/zh-CN/ 语义化版本规范：
- MAJOR.MINOR.PATCH（主.次.修订）
- 0.x：初期开发阶段
- 升级规则：
  - PATCH：向后兼容的缺陷修复  → 0.6.0 → 0.6.1
  - MINOR：向后兼容的功能新增  → 0.6.0 → 0.7.0
  - MAJOR：不兼容的 API 变更   → 0.6.0 → 1.0.0

所有组件（FastAPI 应用 / MCP Server / 包）统一引用本文件，禁止各处手写版本号。
"""
from pathlib import Path

__version__ = "1.3.0"

APP_NAME = "Canteen Recommendation Agent"
APP_TITLE = "食堂菜品推荐与营养分析 Agent"


def _from_pyproject() -> str:
    """尝试从 pyproject.toml 读取版本（若存在且一致）。"""
    try:
        root = Path(__file__).resolve().parents[1]
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version") and "=" in line:
                    raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if raw:
                        return raw
    except Exception:
        pass
    return __version__


# 优先与 pyproject.toml 保持一致（构建/打包时同步）
VERSION = _from_pyproject()