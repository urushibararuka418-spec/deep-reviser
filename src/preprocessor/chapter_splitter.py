"""
ChapterSplitter — 章节识别与段落分割器

功能：
  - 从文本中识别章节边界（中文"第X章"、英文"Chapter X"、Markdown 标题）
  - 将文本按章节切分
  - 按 chunk_size 将章节内容分割为适合 LLM 处理的段落

用法:
    splitter = ChapterSplitter()
    chapters = splitter.split_chapters(text)
    segments = splitter.split_segments(text, chunk_size=1500)
"""

import re
from typing import List, Dict


class ChapterSplitter:
    """章节识别与段落分割器

    识别文本中的章节标记，将文本按章节切分，
    并可按指定 chunk_size 进一步分割为段落。
    """

    # 章节识别正则模式
    # 1. 中文章节: "第X章" 或 "第X节" (X 可以是数字或中文数字)
    # 2. 英文章节: "Chapter X" 或 "CHAPTER X"
    # 3. Markdown 标题: "#" ~ "######" 开头
    CHAPTER_PATTERNS = re.compile(
        r'(?:^|\n)\s*('
        r'第[一二三四五六七八九十百千万\d]+[章节]\s*[^\n]*'   # 中文章节
        r'|Chapter\s+\d+[^\n]*'                              # 英文章节
        r'|#{1,6}\s+[^\n]+'                                  # Markdown 标题
        r')',
        re.MULTILINE | re.IGNORECASE
    )

    def split_chapters(self, text: str) -> List[Dict]:
        """将文本按章节分割

        Args:
            text: 待分割的原始文本

        Returns:
            List[Dict]: 章节列表，每项包含:
                - index: 章节索引 (从 0 开始)
                - title:  章节标题文本
                - content: 章节正文内容
        """
        if not text or not text.strip():
            return []

        # 查找所有章节标题匹配
        matches = list(self.CHAPTER_PATTERNS.finditer(text))

        if not matches:
            # 没有找到任何章节标记，返回单章"全文"
            return [{
                "index": 0,
                "title": "全文",
                "content": text.strip()
            }]

        chapters = []
        for i, match in enumerate(matches):
            title = match.group(1).strip()

            # 确定正文内容的起止位置
            content_start = match.end()
            if i + 1 < len(matches):
                # 内容是当前标题到下一个标题之间的部分
                content_end = matches[i + 1].start()
            else:
                # 最后一章取到文本末尾
                content_end = len(text)

            content = text[content_start:content_end].strip()

            chapters.append({
                "index": i,
                "title": title,
                "content": content
            })

        return chapters

    def split_segments(self, text: str, chunk_size: int = 1500) -> List[Dict]:
        """将文本按章节分割后，再按 chunk_size 切分为段落

        分割逻辑：
        1. 先调用 split_chapters 切分章节
        2. 对每个章节，按 \\n\\n 分割为自然段落
        3. 累积段落直到达到 chunk_size，形成一个 segment
        4. 单个段落超过 chunk_size 时，保持完整不分拆

        Args:
            text: 待分割的原始文本
            chunk_size: 每个段落的最大字符数（默认 1500）

        Returns:
            List[Dict]: 段落列表，每项包含:
                - id:             段落唯一标识
                - chapter_index:  所属章节索引
                - chapter_title:  所属章节标题
                - content:        段落文本内容
        """
        chapters = self.split_chapters(text)
        segments = []
        segment_id = 0

        for chapter in chapters:
            # 按双换行分割为自然段落
            paragraphs = chapter["content"].split("\n\n")
            current_chunk = ""
            current_paragraphs = []

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # 如果当前累积块加上新段落会超过 chunk_size
                if (current_chunk and
                        len(current_chunk) + len(para) + 2 > chunk_size):
                    # 保存当前累积块为一个 segment
                    segments.append({
                        "id": f"seg_{segment_id:04d}",
                        "chapter_index": chapter["index"],
                        "chapter_title": chapter["title"],
                        "content": current_chunk.strip()
                    })
                    segment_id += 1
                    current_chunk = ""
                    current_paragraphs = []

                # 累积段落
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                current_paragraphs.append(para)

            # 保存章节剩余内容
            if current_chunk.strip():
                segments.append({
                    "id": f"seg_{segment_id:04d}",
                    "chapter_index": chapter["index"],
                    "chapter_title": chapter["title"],
                    "content": current_chunk.strip()
                })
                segment_id += 1

        return segments
