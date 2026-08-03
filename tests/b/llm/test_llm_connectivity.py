"""大模型连通性测试（B 拥有）

覆盖本地 Ollama 与云端 API 两种模式：
- 分层探测：DNS 解析 / TCP 连接 / HTTPS 可达性
- 真实 LLM 调用（带重试，容忍网络抖动）
- 可独立运行，不影响其他测试

用法：
    # 测本地 Ollama（USE_CLOUD_API=false）
    uv run python tests/b/llm/test_llm_connectivity.py --local

    # 测云端 API（USE_CLOUD_API=true）
    uv run python tests/b/llm/test_llm_connectivity.py --cloud

    # 全测
    uv run python tests/b/llm/test_llm_connectivity.py
"""
import argparse
import os
import socket
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

# 连通性探测超时（秒）
DNS_TIMEOUT = 5
TCP_TIMEOUT = 8
HTTP_TIMEOUT = 20
LLM_TIMEOUT = 60


def _host_port(url: str):
    u = urlparse(url)
    return u.hostname, u.port or (443 if u.scheme == "https" else 80)


# =============================================================================
# 分层探测
# =============================================================================

def test_dns(url: str) -> bool:
    host, _ = _host_port(url)
    try:
        socket.gethostbyname(host)
        print(f"  [DNS] {host} 解析成功")
        return True
    except Exception as e:
        print(f"  [DNS] 失败: {e}")
        return False


def test_tcp(url: str) -> bool:
    host, port = _host_port(url)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TCP_TIMEOUT)
    try:
        sock.connect((host, port))
        print(f"  [TCP] {host}:{port} 可连接")
        return True
    except Exception as e:
        print(f"  [TCP] 失败: {e}")
        return False
    finally:
        sock.close()


def test_http_reachable(url: str) -> bool:
    """探测 HTTPS 可达性（GET 到 base，能收到任何响应即可达，4xx 属正常）。"""
    try:
        req = urllib.request.Request(url, method="GET")
        urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)
        print(f"  [HTTP] {url} 可达 (200)")
        return True
    except urllib.error.HTTPError as e:
        # 服务器返回 4xx/5xx 说明可达，只是鉴权/路径问题
        print(f"  [HTTP] {url} 可达 (HTTP {e.code})")
        return True
    except Exception as e:
        print(f"  [HTTP] 失败: {e}")
        return False


# =============================================================================
# 真实 LLM 调用（带重试）
# =============================================================================

def call_llm(provider: str, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
    """发起一次最小 LLM 调用，容忍网络抖动。"""
    from langchain_core.messages import HumanMessage

    attempts = 0
    while attempts < max_retries:
        attempts += 1
        try:
            if provider == "local":
                from langchain_ollama import ChatOllama
                llm = ChatOllama(
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                    temperature=0.0,
                    timeout=LLM_TIMEOUT,
                    max_retries=1,
                )
            else:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    api_key=os.getenv("OPENAI_API_KEY", ""),
                    base_url=os.getenv("OPENAI_BASE_URL"),
                    temperature=0.0,
                    timeout=LLM_TIMEOUT,
                    max_retries=1,
                )

            t0 = time.time()
            resp = llm.invoke([HumanMessage(content="回复两个字：OK")])
            dt = time.time() - t0
            content = str(resp.content).strip()
            print(f"  [LLM] 第{attempts}次成功 ({dt:.1f}s): {content!r}")
            return True
        except Exception as e:
            print(f"  [LLM] 第{attempts}次失败: {type(e).__name__}: {str(e)[:120]}")
            if attempts < max_retries:
                time.sleep(retry_delay)
    return False


# =============================================================================
# 汇总
# =============================================================================

def run_connectivity_test(provider: str) -> bool:
    print(f"\n{'='*50}")
    print(f"  测试 {provider.upper()} 大模型连通性")
    print(f"{'='*50}")

    if provider == "local":
        url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    else:
        url = os.getenv("OPENAI_BASE_URL", "")

    print(f"\n  目标: {url}")
    print(f"\n  1. 分层探测")
    ok_dns = test_dns(url)
    ok_tcp = test_tcp(url)
    ok_http = test_http_reachable(url)
    layer_ok = ok_dns and ok_tcp and ok_http

    print(f"\n  2. 真实 LLM 调用")
    llm_ok = call_llm(provider)

    print(f"\n  === 结果 ===")
    print(f"  DNS/TCP/HTTP: {'通过' if layer_ok else '失败'} | LLM 调用: {'通过' if llm_ok else '失败'}")
    return layer_ok and llm_ok


def main():
    parser = argparse.ArgumentParser(description="大模型连通性测试")
    parser.add_argument("--local", action="store_true", help="仅测本地 Ollama")
    parser.add_argument("--cloud", action="store_true", help="仅测云端 API")
    args = parser.parse_args()

    use_cloud = os.getenv("USE_CLOUD_API", "false").lower() in ("1", "true", "yes", "on")
    if not args.local and not args.cloud:
        print("默认按 .env 的 USE_CLOUD_API 判定测试目标")
        args.local = not use_cloud
        args.cloud = use_cloud

    passed = True
    if args.local:
        passed &= run_connectivity_test("local")
    if args.cloud:
        passed &= run_connectivity_test("cloud")

    print(f"\n{'='*50}")
    print(f"  总体: {'全部通过' if passed else '存在失败'}")
    print(f"{'='*50}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
