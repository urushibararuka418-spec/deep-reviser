# DeepReviser — AI长篇小说改文助手 实施计划

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 构建基于 DeepSeek V4 百万上下文的 AI 长篇小说改文助手，实现「全文结构化提取 → 数据库构建 → 精准上下文分段改写」的完整闭环。

**Architecture:** Python 后端 (FastAPI) + 混合数据库 (SQLite + Chroma 向量库) + Gradio 前端。核心思路：百万上下文用于预处理时一次性提取结构化数据，改写时按需检索精准上下文（参照 SillyTavern Lorebook 模式），而非每次全文注入。

**Tech Stack:** Python 3.11+、FastAPI、SQLite、ChromaDB、DeepSeek API、Gradio、python-docx、ebooklib、jieba

**项目路径:** `H:\AI\personalCode\deep-reviser\` (映射为 `/mnt/h/AI/personalCode/deep-reviser/`)

**环境位置:** Windows 原生 Python (conda)，不安装在 WSL 中

---

## Phase Alpha: 核心闭环 MVP (目标 1-2 周)

### Task 1: 项目初始化与环境配置

**Objective:** 在 Windows 上创建项目骨架，配置 Python 虚拟环境和目录结构

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `src/config.py`

**Step 1: 创建项目目录结构**

在 Windows 上 (`H:\AI\personalCode\deep-reviser\`) 创建以下结构：
```
deep-reviser/
├── src/
│   ├── __init__.py
│   ├── config.py          # 配置管理 (API key, DB路径等)
│   ├── preprocessor/      # 预处理模块
│   │   └── __init__.py
│   ├── extractor/         # 信息提取模块
│   │   └── __init__.py
│   ├── database/          # 数据库模块
│   │   └── __init__.py
│   ├── rewriter/          # 改写引擎模块
│   │   └── __init__.py
│   └── ui/                # 前端模块
│       └── __init__.py
├── tests/
│   └── __init__.py
├── data/                  # 用户上传的小说数据
│   └── uploads/
├── db/                    # 本地数据库文件
├── .env.example
├── requirements.txt
└── README.md
```

**Step 2: Windows 上安装 Python 环境**

```powershell
# 在 Windows PowerShell/CMD 中执行（非 WSL！）
# 检查 Python 是否安装
python --version

# 如果没有 conda，先安装 Miniconda
# 下载地址: https://docs.conda.io/en/latest/miniconda.html

# 创建 conda 环境
conda create -n deep-reviser python=3.11 -y
conda activate deep-reviser

# 进入项目目录
cd H:\AI\personalCode\deep-reviser
```

**Step 3: 创建 requirements.txt**

```txt
# Core
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.6.0
pydantic-settings>=2.1.0

# Database
chromadb>=0.4.22
sqlalchemy>=2.0.25

# Document Processing
python-docx>=1.1.0
ebooklib>=0.18
beautifulsoup4>=4.12.0

# AI / LLM
openai>=1.12.0          # DeepSeek API 兼容 OpenAI SDK
tiktoken>=0.5.0

# Text Processing
jieba>=0.42.1
diff-match-patch>=20230430

# Frontend
gradio>=4.18.0

# Utilities
python-dotenv>=1.0.0
rich>=13.7.0
```

**Step 4: 创建 .env.example**

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 数据库路径 (默认项目根目录下的 db/)
DATABASE_URL=sqlite:///db/deep_reviser.db
CHROMA_PERSIST_DIR=db/chroma

# 应用设置
UPLOAD_DIR=data/uploads
MAX_UPLOAD_SIZE_MB=50
```

**Step 5: 创建 src/config.py**

```python
"""配置管理模块"""
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Database
    database_url: str = "sqlite:///db/deep_reviser.db"
    chroma_persist_dir: str = "db/chroma"

    # Upload
    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent

settings = Settings()
```

**Verification:**
```powershell
# Windows 上验证
conda activate deep-reviser
cd H:\AI\personalCode\deep-reviser
pip install -r requirements.txt
python -c "from src.config import settings; print('Config OK:', settings.deepseek_model)"
```

---

### Task 2: 文档预处理模块 — 文件上传与格式转换

**Objective:** 实现 .txt / .docx / .epub 文件的读取和纯文本提取

**Files:**
- Create: `src/preprocessor/file_loader.py`
- Create: `tests/test_file_loader.py`

**Step 1: 编写测试**

```python
# tests/test_file_loader.py
import pytest
from pathlib import Path
from src.preprocessor.file_loader import FileLoader

def test_load_txt_file(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("第一章 开始\n这是一段测试文本。\n第二章 继续\n更多内容。", encoding="utf-8")
    loader = FileLoader()
    text = loader.load(txt_file)
    assert "第一章" in text
    assert "测试文本" in text

def test_load_unsupported_format():
    loader = FileLoader()
    with pytest.raises(ValueError, match="不支持"):
        loader.load(Path("test.pdf"))
```

**Step 2: 验证测试失败** — `pytest tests/test_file_loader.py -v` → FAIL

**Step 3: 编写实现**

```python
# src/preprocessor/file_loader.py
from pathlib import Path
from typing import Union

class FileLoader:
    """多格式文件加载器，将各种格式转换为纯文本"""
    
    SUPPORTED = {".txt", ".md", ".docx", ".epub"}
    
    def load(self, file_path: Union[str, Path]) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED:
            raise ValueError(f"不支持的文件格式: {suffix}，支持: {self.SUPPORTED}")
        
        if suffix == ".txt" or suffix == ".md":
            return self._read_text(path)
        elif suffix == ".docx":
            return self._read_docx(path)
        elif suffix == ".epub":
            return self._read_epub(path)
        return ""
    
    def _read_text(self, path: Path) -> str:
        encodings = ["utf-8", "gbk", "gb2312", "utf-16"]
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError(f"无法解码文件: {path}")
    
    def _read_docx(self, path: Path) -> str:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    
    def _read_epub(self, path: Path) -> str:
        from ebooklib import epub
        from bs4 import BeautifulSoup
        book = epub.read_epub(str(path))
        texts = []
        for item in book.get_items_of_type(9):  # ITEM_DOCUMENT
            soup = BeautifulSoup(item.get_content(), "html.parser")
            texts.append(soup.get_text())
        return "\n\n".join(texts)
```

**Step 4: 运行测试** → `pytest tests/test_file_loader.py -v` → PASS

---

### Task 3: 章节识别与段落分割

**Objective:** 自动识别小说章节标题，按章/段分割文本

**Files:**
- Create: `src/preprocessor/chapter_splitter.py`
- Create: `tests/test_chapter_splitter.py`

**Step 1: 编写测试**

```python
# tests/test_chapter_splitter.py
from src.preprocessor.chapter_splitter import ChapterSplitter

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

def test_detect_chapters():
    splitter = ChapterSplitter()
    chapters = splitter.split_chapters(SAMPLE_TEXT)
    assert len(chapters) == 3
    assert chapters[0]["title"] == "第一章 穿越异世界"
    assert chapters[1]["title"] == "第二章 初遇魔兽"
    assert chapters[2]["title"] == "第三章 觉醒系统"

def test_chapter_content():
    splitter = ChapterSplitter()
    chapters = splitter.split_chapters(SAMPLE_TEXT)
    assert "李明睁开眼睛" in chapters[0]["content"]
    assert "体型巨大的黑狼" in chapters[1]["content"]
    assert "修炼系统" in chapters[2]["content"]

def test_split_segments():
    splitter = ChapterSplitter()
    segments = splitter.split_segments(SAMPLE_TEXT, chunk_size=100)
    assert len(segments) >= 3  # at least 3 segments
```

**Step 2: 验证测试失败** → FAIL

**Step 3: 编写实现**

```python
# src/preprocessor/chapter_splitter.py
import re
from typing import List, Dict
from dataclasses import dataclass, field

@dataclass
class Chapter:
    index: int
    title: str
    content: str
    start_pos: int
    end_pos: int

@dataclass  
class Segment:
    id: str
    chapter_index: int
    content: str
    start_pos: int
    end_pos: int

class ChapterSplitter:
    """章节识别与段落分割器"""
    
    CHAPTER_PATTERNS = [
        r'第[零一二三四五六七八九十百千\d]+章\s*[^\n]*',   # 第X章 标题
        r'Chapter\s+\d+[^\n]*',                            # Chapter X
        r'^#{1,3}\s+.*$',                                  # Markdown headings
    ]
    
    def split_chapters(self, text: str) -> List[Dict]:
        """将全文按章节分割，返回 [{title, content, index}]"""
        pattern = '|'.join(f'({p})' for p in self.CHAPTER_PATTERNS)
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        
        if not matches:
            return [{"index": 0, "title": "全文", "content": text.strip()}]
        
        chapters = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            title = match.group().strip()
            content = text[start:end].strip()
            chapters.append({"index": i, "title": title, "content": content})
        
        return chapters
    
    def split_segments(self, text: str, chunk_size: int = 1500) -> List[Dict]:
        """将文本按段落分割为改写单元 (chunk_size 为字数)"""
        chapters = self.split_chapters(text)
        segments = []
        seg_id = 0
        
        for ch in chapters:
            paragraphs = [p.strip() for p in ch["content"].split("\n") if p.strip()]
            current_chunk = ""
            
            for para in paragraphs:
                if len(current_chunk) + len(para) > chunk_size and current_chunk:
                    segments.append({
                        "id": f"seg_{seg_id:04d}",
                        "chapter_index": ch["index"],
                        "chapter_title": ch["title"],
                        "content": current_chunk.strip(),
                    })
                    seg_id += 1
                    current_chunk = para
                else:
                    current_chunk += "\n" + para if current_chunk else para
            
            if current_chunk:
                segments.append({
                    "id": f"seg_{seg_id:04d}",
                    "chapter_index": ch["index"],
                    "chapter_title": ch["title"],
                    "content": current_chunk.strip(),
                })
                seg_id += 1
        
        return segments
```

**Step 4: 运行测试** → PASS

---

### Task 4: DeepSeek API 客户端封装

**Objective:** 封装 DeepSeek API 调用，支持百万上下文的结构化提取

**Files:**
- Create: `src/extractor/ds_client.py`
- Create: `tests/test_ds_client.py` (mock 测试)

**Step 1: 编写测试**

```python
# tests/test_ds_client.py
from unittest.mock import patch, MagicMock
from src.extractor.ds_client import DeepSeekClient

def test_client_initialization():
    client = DeepSeekClient(api_key="test_key")
    assert client.api_key == "test_key"

@patch("openai.OpenAI")
def test_extract_json(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"result": "ok"}'))]
    )
    
    client = DeepSeekClient(api_key="test_key")
    result = client.extract_json("prompt", "text")
    assert result == {"result": "ok"}
```

**Step 2: 验证失败** → FAIL

**Step 3: 编写实现**

```python
# src/extractor/ds_client.py
import json
import re
from openai import OpenAI
from src.config import settings

class DeepSeekClient:
    """DeepSeek V4 API 客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.client = OpenAI(
            api_key=api_key or settings.deepseek_api_key,
            base_url=base_url or settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model
    
    def chat(self, messages: list, **kwargs) -> str:
        """通用对话"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content
    
    def extract_json(self, system_prompt: str, user_content: str) -> dict:
        """结构化提取 — 返回 JSON"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        raw = self.chat(messages, temperature=0.1, response_format={"type": "json_object"})
        return self._parse_json(raw)
    
    def _parse_json(self, text: str) -> dict:
        """鲁棒的 JSON 解析"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 尝试提取 ```json 代码块
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"无法解析 JSON: {text[:200]}")
```

**Step 4: 运行测试** → PASS

---

### Task 5: 角色提取器

**Objective:** 利用 DeepSeek V4 从全文中提取角色信息并结构化存储

**Files:**
- Create: `src/extractor/character_extractor.py`
- Create: `tests/test_character_extractor.py`

**Step 1: 编写测试**

```python
# tests/test_character_extractor.py
from unittest.mock import patch
from src.extractor.character_extractor import CharacterExtractor

@patch("src.extractor.ds_client.DeepSeekClient.extract_json")
def test_extract_characters(mock_extract):
    mock_extract.return_value = {
        "characters": [
            {
                "name": "李明",
                "aliases": ["小明", "李兄"],
                "role_type": "主角",
                "personality_traits": ["勇敢", "谨慎"],
                "first_appearance": "第一章",
            }
        ]
    }
    extractor = CharacterExtractor()
    result = extractor.extract("测试小说全文...")
    assert len(result["characters"]) == 1
    assert result["characters"][0]["name"] == "李明"
```

**Step 2-4: TDD 循环** (略，同上模式)

```python
# src/extractor/character_extractor.py
from src.extractor.ds_client import DeepSeekClient

CHARACTER_EXTRACTION_PROMPT = """你是一位专业的小说分析助手。请从以下小说全文中提取所有角色信息。

对每个角色，请提取以下字段：
- name: 角色姓名
- aliases: 所有别名/称呼列表
- role_type: 主角/配角/反派/路人
- personality_traits: 性格标签列表
- abilities: 能力/技能列表
- relationships: 与其他角色的关系 [{target, relation, description}]
- character_arc: 角色成长线简述
- first_appearance: 首次出场章节
- quote_examples: 代表性格的对话片段（2-3条）

请以严格的 JSON 格式输出。"""

class CharacterExtractor:
    def __init__(self, client: DeepSeekClient = None):
        self.client = client or DeepSeekClient()
    
    def extract(self, full_text: str) -> dict:
        return self.client.extract_json(CHARACTER_EXTRACTION_PROMPT, full_text)
```

---

### Task 6: SQLite 数据库模型

**Objective:** 使用 SQLAlchemy 定义核心数据表

**Files:**
- Create: `src/database/models.py`
- Create: `src/database/session.py`

```python
# src/database/models.py
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True)
    index = Column(Integer)
    title = Column(String(500))
    content = Column(Text)
    char_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)

class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    aliases = Column(JSON)
    role_type = Column(String(50))
    personality_traits = Column(JSON)
    abilities = Column(JSON)
    relationships = Column(JSON)
    character_arc = Column(Text)
    first_appearance = Column(String(200))
    quote_examples = Column(JSON)

class WorldSetting(Base):
    __tablename__ = "world_settings"
    id = Column(Integer, primary_key=True)
    category = Column(String(100))  # 地点/势力/道具/规则/历史
    name = Column(String(300))
    keywords = Column(JSON)  # 触发关键词列表
    description = Column(Text)
    first_chapter = Column(String(200))

class PlotEvent(Base):
    __tablename__ = "plot_events"
    id = Column(Integer, primary_key=True)
    chapter_index = Column(Integer)
    summary = Column(Text)
    participants = Column(JSON)  # 参与角色名列表
    location = Column(String(300))
    cause_events = Column(JSON)
    consequence_events = Column(JSON)

class StyleBaseline(Base):
    __tablename__ = "style_baseline"
    id = Column(Integer, primary_key=True)
    pace = Column(String(50))
    sentence_length_preference = Column(String(50))
    dialogue_ratio = Column(String(50))
    tone = Column(String(100))
    common_rhetoric = Column(JSON)
    forbidden_patterns = Column(JSON)

class RewriteHistory(Base):
    __tablename__ = "rewrite_history"
    id = Column(Integer, primary_key=True)
    segment_id = Column(String(50))
    original_text = Column(Text)
    rewritten_text = Column(Text)
    instruction = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

# src/database/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    from src.database.models import Base
    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### 后续 Tasks (简要 — 根据实际进展展开)

| Task | 目标 | 文件 |
|------|------|------|
| 7 | 世界设定提取器 (Lorebook 模式) | `src/extractor/lore_extractor.py` |
| 8 | 剧情事件与伏笔提取器 | `src/extractor/plot_extractor.py` |
| 9 | 风格基线提取器 | `src/extractor/style_extractor.py` |
| 10 | ChromaDB 向量存储集成 | `src/database/vector_store.py` |
| 11 | 上下文组装引擎 (语义检索+角色+Lorebook) | `src/rewriter/context_assembler.py` |
| 12 | 分段改写引擎 | `src/rewriter/rewrite_engine.py` |
| 13 | 一致性校验与 diff 对比 | `src/rewriter/consistency_checker.py` |
| 14 | Gradio Web UI — 上传与项目管理 | `src/ui/app.py` |
| 15 | Gradio Web UI — 改文工作台 | `src/ui/rewrite_workspace.py` |

---

## 关键技术决策

1. **SQLite 而非 PostgreSQL**: MVP 阶段使用 SQLite，零配置，数据文件直接存储在项目 `db/` 目录
2. **ChromaDB 而非 Milvus**: ChromaDB 轻量级，pip install 即用，适合单机场景
3. **Gradio 而非 Streamlit**: Gradio 更适合 AI/ML 类应用，组件更丰富
4. **环境在 Windows 原生**: 用户要求环境不装在 WSL，使用 conda 在 Windows 上管理
5. **DeepSeek API 通过 OpenAI SDK**: DeepSeek API 兼容 OpenAI 格式，直接用 openai 库调用

## 运行方式

```powershell
# Windows PowerShell
conda activate deep-reviser
cd H:\AI\personalCode\deep-reviser

# 初始化数据库
python -c "from src.database.session import init_db; init_db()"

# 启动 Web UI
python -m src.ui.app

# 运行测试
pytest tests/ -v
```

---

> **下一步:** 请确认此 Plan，然后我将逐步执行 Tasks 1-6 的代码编写，并在 Windows 上配置环境。
