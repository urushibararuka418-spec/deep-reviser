"""
FileLoader — 多格式文档加载器
=============================
支持格式：.txt / .md / .docx / .epub
自动检测文本编码（UTF-8 / GBK / GB2312 / UTF-16）。
"""

import os
from pathlib import Path


class FileLoader:
    """多格式文档加载器。

    根据文件后缀名自动选择对应的读取策略：
        - .txt / .md  → 文本模式，自动检测编码
        - .docx       → python-docx 提取段落
        - .epub       → ebooklib + BeautifulSoup 提取
    """

    # 支持的文件后缀集合
    SUPPORTED: set[str] = {".txt", ".md", ".docx", ".epub"}

    # ── 文本编码探测顺序 ──────────────────────────────
    _TEXT_ENCODINGS: list[str] = ["utf-8", "gbk", "gb2312", "utf-16"]

    # ── 公共 API ──────────────────────────────────────

    def load(self, file_path: str | Path) -> str:
        """加载文档，返回纯文本内容。

        Args:
            file_path: 文件路径。

        Returns:
            str: 文档的纯文本内容。

        Raises:
            FileNotFoundError: 文件不存在。
            ValueError: 不支持的文件格式。
        """
        file_path = Path(file_path)

        # 检查文件是否存在
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 根据后缀分发
        suffix = file_path.suffix.lower()

        if suffix in {".txt", ".md"}:
            return self._read_text(file_path)
        elif suffix == ".docx":
            return self._read_docx(file_path)
        elif suffix == ".epub":
            return self._read_epub(file_path)
        else:
            raise ValueError(
                f"不支持的文件格式: {suffix}。"
                f"支持的格式: {', '.join(sorted(self.SUPPORTED))}"
            )

    # ── 文本文件读取（多编码探测）─────────────────────

    def _read_text(self, file_path: Path) -> str:
        """读取纯文本文件，依次尝试多种编码直到成功。

        编码探测顺序：UTF-8 → GBK → GB2312 → UTF-16
        """
        # 先按二进制读取，然后依次尝试解码
        raw_bytes = file_path.read_bytes()

        for encoding in self._TEXT_ENCODINGS:
            try:
                text = raw_bytes.decode(encoding)
                # 标准化换行符：\r\n → \n（跨平台一致性）
                return text.replace("\r\n", "\n")
            except (UnicodeDecodeError, UnicodeError):
                continue

        # 所有编码都失败，用 UTF-8 并忽略错误作为兜底
        text = raw_bytes.decode("utf-8", errors="replace")
        return text.replace("\r\n", "\n")

    # ── DOCX 读取 ─────────────────────────────────────

    def _read_docx(self, file_path: Path) -> str:
        """读取 .docx 文件，提取所有段落文本。

        使用 python-docx 库，按段落顺序拼接，
        段落之间用换行符分隔。
        """
        from docx import Document

        doc = Document(str(file_path))
        paragraphs: list[str] = []

        for para in doc.paragraphs:
            text = para.text
            if text:  # 跳过空段落
                paragraphs.append(text)

        return "\n".join(paragraphs)

    # ── EPUB 读取 ─────────────────────────────────────

    def _read_epub(self, file_path: Path) -> str:
        """读取 .epub 电子书，提取所有章节文本。

        使用 ebooklib 解析 epub，BeautifulSoup 提取 HTML 文本内容，
        各章节之间用双换行分隔。
        """
        from ebooklib import epub
        from bs4 import BeautifulSoup

        book = epub.read_epub(str(file_path))
        chapters: list[str] = []

        for item in book.get_items_of_type(9):  # ITEM_DOCUMENT = 9
            # 解析 HTML 内容
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            if text.strip():
                chapters.append(text)

        return "\n\n".join(chapters)
