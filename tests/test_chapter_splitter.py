"""
ChapterSplitter 测试 — 章节识别与段落分割器
严格按照 TDD 流程：先写测试，确认失败，再实现功能
"""

import pytest
from src.preprocessor.chapter_splitter import ChapterSplitter

# 测试用样本文本，包含中文章节标记
SAMPLE_TEXT = """
第一章 穿越异世界
李明睁开眼睛，发现自己躺在一片陌生的森林里。

他记得自己刚才还在公司加班，怎么眨眼的功夫就到了这里？

第二章 初遇魔兽
一声低沉的吼叫从灌木丛后传来。

李明警觉地转身，看到一只体型巨大的黑狼。

第三章 觉醒系统
【叮！宿主已激活修炼系统】

一个半透明的面板浮现在李明眼前。
"""


class TestChapterSplitter:
    """ChapterSplitter 单元测试套件"""

    def test_detect_chapters(self):
        """测试：正确识别三个章节及标题"""
        splitter = ChapterSplitter()
        chapters = splitter.split_chapters(SAMPLE_TEXT)

        assert len(chapters) == 3, f"应检测到 3 个章节，实际: {len(chapters)}"

        assert chapters[0]["index"] == 0
        assert chapters[0]["title"] == "第一章 穿越异世界"

        assert chapters[1]["index"] == 1
        assert chapters[1]["title"] == "第二章 初遇魔兽"

        assert chapters[2]["index"] == 2
        assert chapters[2]["title"] == "第三章 觉醒系统"

    def test_chapter_content(self):
        """测试：每个章节包含对应内容"""
        splitter = ChapterSplitter()
        chapters = splitter.split_chapters(SAMPLE_TEXT)

        # 第一章内容应包含"李明睁开眼睛"
        assert "李明睁开眼睛" in chapters[0]["content"]
        assert "发现自己躺在一片陌生的森林里" in chapters[0]["content"]

        # 第二章内容应包含"灌木丛后传来"、"黑狼"
        assert "灌木丛后传来" in chapters[1]["content"]
        assert "黑狼" in chapters[1]["content"]

        # 第三章内容应包含"修炼系统"、"半透明的面板"
        assert "修炼系统" in chapters[2]["content"]
        assert "半透明的面板" in chapters[2]["content"]

    def test_split_segments(self):
        """测试：按 chunk_size 分割段落"""
        splitter = ChapterSplitter()
        segments = splitter.split_segments(SAMPLE_TEXT, chunk_size=100)

        # chunk_size=100 时，500+ 字的文本应该至少分为 3 段
        assert len(segments) >= 3, f"chunk_size=100 时至少应有 3 段，实际: {len(segments)}"

        # 每段长度不应超过 chunk_size 太多（允许一个段落的误差）
        for seg in segments:
            assert len(seg["content"]) <= 150, (
                f"段落过长: {len(seg['content'])} 字符 (chunk_size=100)"
            )

        # 检查段 ID 和章节信息
        for seg in segments:
            assert "id" in seg
            assert "chapter_index" in seg
            assert "chapter_title" in seg
            assert "content" in seg

    def test_no_chapter_pattern(self):
        """测试：无章节标记的文本返回单章"全文" """
        splitter = ChapterSplitter()
        plain_text = "这是一段没有任何章节标记的普通文本。\n\n它只有几个段落而已。"

        chapters = splitter.split_chapters(plain_text)

        assert len(chapters) == 1, f"无章节标记应返回单章，实际: {len(chapters)}"
        assert chapters[0]["index"] == 0
        assert chapters[0]["title"] == "全文"
        assert "普通文本" in chapters[0]["content"]
