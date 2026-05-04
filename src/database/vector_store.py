"""ChromaDB 向量存储封装。"""
from pathlib import Path

from chromadb import PersistentClient
from chromadb.utils import embedding_functions

from src.config import settings


class VectorStore:
    """封装 ChromaDB PersistentClient 与默认 collections。"""

    def __init__(self, persist_directory: str | None = None):
        persist_path = Path(persist_directory or settings.chroma_persist_dir)
        if not persist_path.is_absolute():
            persist_path = settings.project_root / persist_path
        persist_path.mkdir(parents=True, exist_ok=True)

        self.persist_directory = persist_path
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        self.client = PersistentClient(path=str(self.persist_directory))
        self._init_collections()

    def _init_collections(self):
        """创建默认使用的两个 collections。"""
        self.novel_segments = self.client.get_or_create_collection(
            name="novel_segments",
            embedding_function=self.embedding_function,
        )
        self.lorebook_entries = self.client.get_or_create_collection(
            name="lorebook_entries",
            embedding_function=self.embedding_function,
        )

    def add_segments(self, texts, metadatas):
        """向小说分段 collection 添加文本。"""
        self._add_documents(self.novel_segments, texts, metadatas, id_prefix="segment")

    def add_lore_entries(self, texts, metadatas):
        """向 lorebook collection 添加文本。"""
        self._add_documents(self.lorebook_entries, texts, metadatas, id_prefix="lore")

    def search(self, collection_name, query, k=5):
        """检索相似文档并标准化返回结构。"""
        collection = self.client.get_collection(
            collection_name,
            embedding_function=self.embedding_function,
        )
        results = collection.query(query_texts=[query], n_results=k)

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        normalized = []
        for doc_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            normalized.append(
                {
                    "id": doc_id,
                    "text": document,
                    "metadata": metadata,
                    "distance": distance,
                }
            )
        return normalized

    def _add_documents(self, collection, texts, metadatas, id_prefix):
        """使用递增 ID 添加文档，避免调用方额外提供 ids。"""
        start_index = collection.count()
        ids = [f"{id_prefix}_{start_index + index}" for index in range(len(texts))]
        collection.add(documents=texts, metadatas=metadatas, ids=ids)
