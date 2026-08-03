import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

from rag.retriever import (
    ChromaDishRetriever,
    retrieve_dishes,
    _tokenize,
    DeterministicEmbeddings,
)
from db import get_db

_tmp_dirs = []


def _new_retriever():
    tmp = tempfile.mkdtemp(prefix="test_chroma_rag_")
    _tmp_dirs.append(tmp)
    return ChromaDishRetriever(get_db().get_all_dishes(), persist_dir=tmp)


def test_tokenize():
    t = _tokenize("红烧肉")
    assert "红烧" in t and "烧肉" in t, f"should produce bigrams: {t}"
    print("  tokenize bigrams: OK")


def test_retrieve_spicy_meat():
    r = _new_retriever()
    res = r.retrieve("辣的水煮肉", 5)
    assert len(res) == 5, "should return 5 results"
    assert all("dish" in item and "score" in item for item in res)
    names = [item["dish"]["name"] for item in res]
    print(f"  spicy query: {names}")


def test_retrieve_light_veggie():
    r = _new_retriever()
    res = r.retrieve("清淡的素菜", 3)
    assert len(res) == 3
    print(f"  light query: {[item['dish']['name'] for item in res]}")


def test_retrieve_sorted():
    r = _new_retriever()
    res = r.retrieve("辣", 10)
    scores = [item["score"] for item in res]
    assert scores == sorted(scores, reverse=True), "should be sorted descending"
    print(f"  sorted scores: {scores}")


def test_chroma_index_persists():
    tmp = os.path.join(tempfile.gettempdir(), "test_chroma_persist")
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    r = ChromaDishRetriever(get_db().get_all_dishes(), persist_dir=tmp)
    assert os.path.isdir(tmp), "chroma should persist to directory"
    assert r.dishes, "should hold dishes"
    print(f"  chroma persisted: {os.path.isdir(tmp)}")


def test_deterministic_embeddings():
    emb = DeterministicEmbeddings()
    v = emb.embed_query("红烧肉")
    assert len(v) > 0
    # same input -> same vector
    assert emb.embed_query("红烧肉") == v, "deterministic"
    print(f"  deterministic embedding dim: {len(v)}")


def test_retrieve_no_match():
    r = _new_retriever()
    res = r.retrieve("zzzz不存在的东西", 5)
    assert len(res) == 5, "should still return top results (low score)"
    print(f"  no-match still returns {len(res)} results")


if __name__ == "__main__":
    tests = [
        test_tokenize,
        test_retrieve_spicy_meat,
        test_retrieve_light_veggie,
        test_retrieve_sorted,
        test_chroma_index_persists,
        test_deterministic_embeddings,
        test_retrieve_no_match,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {t.__name__} - {e}")
    for d in _tmp_dirs:
        shutil.rmtree(d, ignore_errors=True)
    print(f"\n{passed}/{len(tests)} tests passed")