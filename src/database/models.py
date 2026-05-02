"""SQLite 数据库 ORM 模型定义"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """声明式基类"""
    pass


class Chapter(Base):
    """章节表 - 存储每章原文与元信息"""
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True)                      # 主键
    index = Column(Integer)                                     # 章节序号
    title = Column(String(500))                                 # 章节标题
    content = Column(Text)                                      # 章节原文
    char_count = Column(Integer)                                # 字数统计
    created_at = Column(DateTime, default=datetime.now)          # 创建时间


class Character(Base):
    """角色表 - 存储角色档案"""
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True)                      # 主键
    name = Column(String(200))                                  # 角色名
    aliases = Column(JSON)                                      # 别名列表
    role_type = Column(String(50))                              # 角色类型（主角/配角/反派等）
    personality_traits = Column(JSON)                           # 性格特征
    abilities = Column(JSON)                                    # 能力/技能
    relationships = Column(JSON)                                # 人际关系
    character_arc = Column(Text)                                # 角色弧光
    first_appearance = Column(String(200))                      # 首次出场章节
    quote_examples = Column(JSON)                               # 经典语录示例


class WorldSetting(Base):
    """世界观设定表"""
    __tablename__ = "world_settings"

    id = Column(Integer, primary_key=True)                      # 主键
    category = Column(String(100))                              # 分类（地理/历史/势力等）
    name = Column(String(300))                                  # 设定名称
    keywords = Column(JSON)                                     # 关键词
    description = Column(Text)                                  # 详细描述
    first_chapter = Column(String(200))                         # 首次出现章节


class PlotEvent(Base):
    """剧情事件表 - 存储关键剧情节点"""
    __tablename__ = "plot_events"

    id = Column(Integer, primary_key=True)                      # 主键
    chapter_index = Column(Integer)                             # 所属章节序号
    summary = Column(Text)                                      # 事件摘要
    participants = Column(JSON)                                 # 参与角色
    location = Column(String(300))                              # 发生地点
    cause_events = Column(JSON)                                 # 前因事件
    consequence_events = Column(JSON)                           # 后果事件


class StyleBaseline(Base):
    """风格基线表 - 存储作品风格特征"""
    __tablename__ = "style_baseline"

    id = Column(Integer, primary_key=True)                      # 主键
    pace = Column(String(50))                                   # 节奏（快/中/慢）
    sentence_length_preference = Column(String(50))             # 句子长度偏好
    dialogue_ratio = Column(String(50))                         # 对话占比
    tone = Column(String(100))                                  # 语气/基调
    common_rhetoric = Column(JSON)                              # 常用修辞手法
    forbidden_patterns = Column(JSON)                           # 禁止使用的模式


class RewriteHistory(Base):
    """改写历史表 - 记录每次改写操作"""
    __tablename__ = "rewrite_history"

    id = Column(Integer, primary_key=True)                      # 主键
    segment_id = Column(String(50))                             # 段落标识
    original_text = Column(Text)                                # 原始文本
    rewritten_text = Column(Text)                               # 改写后文本
    instruction = Column(Text)                                  # 改写指令
    created_at = Column(DateTime, default=datetime.now)          # 改写时间
