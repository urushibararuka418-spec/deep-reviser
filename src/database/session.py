"""数据库会话管理 - SQLite 引擎、会话工厂与初始化"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from pathlib import Path


# 解析数据库路径，确保 db 目录存在
db_path = Path(settings.database_url.replace("sqlite:///", ""))
if not db_path.is_absolute():
    # 相对路径 → 相对于项目根目录
    db_path = Path(__file__).parent.parent.parent / db_path
db_path.parent.mkdir(parents=True, exist_ok=True)

# 数据库引擎（echo=False 关闭 SQL 日志）
engine = create_engine(f"sqlite:///{db_path}", echo=False)

# 会话工厂
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """初始化数据库 - 创建所有表（若不存在）"""
    from src.database.models import Base
    Base.metadata.create_all(engine)


def get_db():
    """依赖注入用：获取数据库会话的生成器
    
    用法：
        db = next(get_db())
        try:
            ... 
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
