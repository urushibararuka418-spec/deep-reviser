"""数据库模型与Session的单元测试"""
import pytest
from sqlalchemy import inspect, text
from src.database.models import Base, Chapter, Character, WorldSetting, PlotEvent, StyleBaseline, RewriteHistory
from src.database.session import engine, init_db, SessionLocal


class TestModels:
    """测试数据库模型的字段定义"""

    def test_chapter_model_fields(self):
        """验证 Chapter 表字段"""
        inspector = inspect(Chapter)
        columns = {c.key for c in inspector.columns}
        expected = {"id", "index", "title", "content", "char_count", "created_at"}
        assert expected.issubset(columns)

    def test_character_model_fields(self):
        """验证 Character 表字段"""
        inspector = inspect(Character)
        columns = {c.key for c in inspector.columns}
        expected = {"id", "name", "aliases", "role_type", "personality_traits",
                    "abilities", "relationships", "character_arc", "first_appearance", "quote_examples"}
        assert expected.issubset(columns)

    def test_world_setting_model_fields(self):
        """验证 WorldSetting 表字段"""
        inspector = inspect(WorldSetting)
        columns = {c.key for c in inspector.columns}
        expected = {"id", "category", "name", "keywords", "description", "first_chapter"}
        assert expected.issubset(columns)

    def test_plot_event_model_fields(self):
        """验证 PlotEvent 表字段"""
        inspector = inspect(PlotEvent)
        columns = {c.key for c in inspector.columns}
        expected = {"id", "chapter_index", "summary", "participants", "location", "cause_events", "consequence_events"}
        assert expected.issubset(columns)

    def test_style_baseline_model_fields(self):
        """验证 StyleBaseline 表字段"""
        inspector = inspect(StyleBaseline)
        columns = {c.key for c in inspector.columns}
        expected = {"id", "pace", "sentence_length_preference", "dialogue_ratio",
                    "tone", "common_rhetoric", "forbidden_patterns"}
        assert expected.issubset(columns)

    def test_rewrite_history_model_fields(self):
        """验证 RewriteHistory 表字段"""
        inspector = inspect(RewriteHistory)
        columns = {c.key for c in inspector.columns}
        expected = {"id", "segment_id", "original_text", "rewritten_text", "instruction", "created_at"}
        assert expected.issubset(columns)


class TestDatabaseInit:
    """测试数据库初始化和 CRUD 操作"""

    def test_init_db_creates_tables(self):
        """验证 init_db 创建所有表（使用内存数据库）"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(test_engine)

        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "chapters" in tables
        assert "characters" in tables
        assert "world_settings" in tables
        assert "plot_events" in tables
        assert "style_baseline" in tables
        assert "rewrite_history" in tables

    def test_session_crud(self):
        """验证基本 CRUD 操作"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        db = TestSession()

        # Create: 创建记录
        ch = Chapter(index=0, title="测试章节", content="测试内容", char_count=4)
        db.add(ch)
        db.commit()

        # Read: 读取记录
        result = db.query(Chapter).filter_by(title="测试章节").first()
        assert result is not None
        assert result.content == "测试内容"

        # Update: 更新记录
        result.title = "新标题"
        db.commit()
        assert db.query(Chapter).first().title == "新标题"

        # Delete: 删除记录
        db.delete(result)
        db.commit()
        assert db.query(Chapter).count() == 0

        db.close()
