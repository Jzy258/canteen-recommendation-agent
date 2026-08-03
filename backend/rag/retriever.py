"""
菜品 RAG 检索链路（B 拥有 · Chroma 向量库实现）

链路：向量化（Embeddings）→ 入库（Chroma）→ 召回排序（similarity_search）

实现要点：
1. 向量化：优先使用 Ollama 本地 embedding（nomic-embed-text），
   不可用时回退到自研确定性 TF+bigram 向量（保证离线/无 LLM 可用）。
2. 存储：langchain-chroma 的 Chroma 向量库，持久化到 data/chroma_db。
3. 召回排序：Chroma.similarity_search_with_score 按距离排序取 top_k，
   再对命中条目做名称/标签精确命中加权，输出统一结构。
"""
import math
import os
import zlib

from langchain_core.tools import tool
from langchain_core.embeddings import Embeddings
from db import get_db

# =============================================================================
# 切词（自研中文轻量切词）
# =============================================================================

_STOP = {"一个", "一些", "有点", "比较", "菜", "食堂", "吃什么"}


def _tokenize(text: str) -> list[str]:
    """按 1~2 字滑窗切出候选词（中文用 bigram 兜底单字）。"""
    text = str(text or "")
    tokens = []
    for ch in text:
        if ch.strip() and not ch.isspace():
            tokens.append(ch)
    for i in range(len(text) - 1):
        pair = text[i:i + 2]
        if pair.strip():
            tokens.append(pair)
    tokens += [w for w in text.replace(",", " ").split() if w]
    return [t for t in tokens if t and t not in _STOP and t != " "]


# =============================================================================
# Embeddings：Ollama 优先，自研确定性向量回退
# =============================================================================

class DeterministicEmbeddings(Embeddings):
    """自研确定性 Embeddings：TF + bigram 哈希向量（无 LLM 也可用）。"""

    def __init__(self):
        self._vocab: dict[str, int] = {}
        self._dim = 256

    def _expand(self, features: list[str]) -> dict[str, int]:
        """记录新词并返回计数 dict。"""
        counts: dict[str, int] = {}
        for f in features:
            counts[f] = counts.get(f, 0) + 1
        return counts

    def _build(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for f in _tokenize(text):
            # 用 zlib.crc32 确定性哈希（Python 内置 hash() 受 PYTHONHASHSEED 影响，
            # 跨进程不一致会导致 Chroma 持久化索引在重启后失效）
            idx = zlib.crc32(f.encode("utf-8")) % self._dim
            vec[idx] += 1.0
        # 归一化
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._build(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._build(text)


_ollama_embeddings = None
_deterministic_embeddings = None


def get_embeddings() -> Embeddings:
    global _ollama_embeddings, _deterministic_embeddings
    # 尝试 Ollama embedding（有模型则用之，语义更强）
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    if _ollama_embeddings is None:
        try:
            from langchain_ollama import OllamaEmbeddings
            _ollama_embeddings = OllamaEmbeddings(base_url=base, model=model)
        except Exception:
            _ollama_embeddings = None
    if _ollama_embeddings is not None:
        try:
            # 探测 Ollama 是否在线
            _ollama_embeddings.embed_query("ping")
            return _ollama_embeddings
        except Exception:
            pass
    if _deterministic_embeddings is None:
        _deterministic_embeddings = DeterministicEmbeddings()
    return _deterministic_embeddings


# =============================================================================
# Chroma 向量库检索器
# =============================================================================

def _dish_text(dish: dict) -> str:
    """生成菜品的检索文本（名称 + 类别 + 口味 + 描述）。"""
    parts = [
        dish.get("name", ""),
        dish.get("category", ""),
        dish.get("flavor_tags", ""),
    ]
    return " ".join(p for p in parts if p)


class ChromaDishRetriever:
    def __init__(self, dishes: list[dict], persist_dir: str | None = None,
                 collection_name: str = "dishes"):
        self.dishes = dishes
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._build_index()

    def _build_index(self):
        from langchain_chroma import Chroma
        texts = [_dish_text(d) for d in self.dishes]
        metadatas = [dict(d) for d in self.dishes]
        ids = [str(d["id"]) for d in self.dishes]
        kwargs = {}
        if self.persist_dir:
            kwargs["persist_directory"] = self.persist_dir
        self._chroma = Chroma.from_texts(
            texts=texts,
            embedding=get_embeddings(),
            metadatas=metadatas,
            ids=ids,
            collection_name=self.collection_name,
            **kwargs,
        )

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Chroma 召回 + 排序：返回 [{dish, score, similarity}]。"""
        results = self._chroma.similarity_search_with_score(query, k=top_k)
        out = []
        for doc, distance in results:
            dish = dict(doc.metadata)
            # Chroma 默认返回距离（越小越近），转相似度 [0,1]
            sim = max(0.0, 1.0 - float(distance))
            boost = 0.0
            # 名称/标签精确命中加权
            if any(f in doc.page_content for f in _tokenize(query)):
                boost = 0.3
            out.append({
                "dish": dish,
                "score": round(sim + boost, 4),
                "similarity": round(sim, 4),
            })
        # 按最终得分降序（boost 可能改变 Chroma 默认距离序）
        out.sort(key=lambda x: x["score"], reverse=True)
        return out


# 全局缓存
_retriever_cache: dict[int, ChromaDishRetriever] = {}


def get_retriever() -> ChromaDishRetriever:
    db = get_db()
    dishes = db.get_all_dishes()
    key = len(dishes)
    if key not in _retriever_cache:
        persist = os.getenv("CHROMA_DB_PATH", "backend/data/chroma_db")
        _retriever_cache[key] = ChromaDishRetriever(dishes, persist_dir=persist)
    return _retriever_cache[key]


# =============================================================================
# @tool：近似菜品检索
# =============================================================================

@tool
def retrieve_dishes(query: str, top_k: int = 5) -> list[dict]:
    """按语义/关键词近似检索菜品（RAG + Chroma 向量库）。查询不存在或记不清菜名时，
    返回与描述最相关的菜品，每条附相似度 score。
    Args:
        query: 描述性查询，如 "麻辣的水煮菜"。
        top_k: 返回数量，默认 5。
    """
    retriever = get_retriever()
    return retriever.retrieve(query, top_k)