"""VectorStore 的单元测试"""
from chromadb import PersistentClient

from src.database.vector_store import VectorStore


def test_init_creates_collections(tmp_path):
    """初始化后应创建两个默认 collection"""
    store = VectorStore(persist_directory=str(tmp_path))

    assert store.client.get_collection("novel_segments") is not None
    assert store.client.get_collection("lorebook_entries") is not None


def test_add_and_search_segments(tmp_path):
    """添加段落后应能检索到相似文本"""
    store = VectorStore(persist_directory=str(tmp_path))
    texts = [
        "Dragon fire scorched the battlefield under a crimson sky.",
        "The scholar quietly copied notes in the library.",
    ]
    metadatas = [
        {"chapter": 1, "label": "battle"},
        {"chapter": 2, "label": "library"},
    ]

    store.add_segments(texts, metadatas)
    results = store.search("novel_segments", texts[0], k=1)

    assert len(results) == 1
    assert results[0]["text"] == texts[0]
    assert results[0]["metadata"] == metadatas[0]


def test_search_returns_k_results(tmp_path):
    """search(k=3) 应返回 3 条结果"""
    store = VectorStore(persist_directory=str(tmp_path))
    texts = [
        "A dragon rests on the mountain peak.",
        "A dragon guards the ancient gate.",
        "A dragon circles above the clouds.",
        "Rain falls across the silent town.",
    ]
    metadatas = [{"index": i} for i in range(len(texts))]

    store.add_segments(texts, metadatas)
    results = store.search("novel_segments", "dragon", k=3)

    assert len(results) == 3


def test_add_lorebook_entries(tmp_path):
    """应能向 lorebook_entries collection 添加并检索条目"""
    store = VectorStore(persist_directory=str(tmp_path))
    texts = [
        "Skyforge City is the capital of the northern kingdom.",
        "Moonwell Forest is sacred to the druids.",
    ]
    metadatas = [
        {"type": "location", "name": "Skyforge City"},
        {"type": "location", "name": "Moonwell Forest"},
    ]

    store.add_lore_entries(texts, metadatas)
    results = store.search("lorebook_entries", texts[0], k=1)

    assert len(results) == 1
    assert results[0]["text"] == texts[0]
    assert results[0]["metadata"] == metadatas[0]


def test_persist_directory(tmp_path):
    """数据应持久化到指定目录并可被新实例读取"""
    persist_dir = tmp_path / "chroma_store"
    texts = ["The silver tower overlooks the capital city."]
    metadatas = [{"chapter": 3, "tag": "setting"}]

    store = VectorStore(persist_directory=str(persist_dir))
    store.add_segments(texts, metadatas)

    reloaded_store = VectorStore(persist_directory=str(persist_dir))
    results = reloaded_store.search("novel_segments", texts[0], k=1)

    assert persist_dir.exists()
    assert len(list(persist_dir.iterdir())) > 0
    assert len(results) == 1
    assert results[0]["text"] == texts[0]

    client = PersistentClient(path=str(persist_dir))
    assert client.get_collection("novel_segments") is not None
