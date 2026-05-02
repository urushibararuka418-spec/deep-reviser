# DeepReviser — AI 长篇小说改文助手

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-37%20passed-green)]()

基于 **DeepSeek V4 百万上下文** 的 AI 长篇小说改文助手。先利用超长上下文一次性提取全书结构化信息（角色/世界观/剧情/伏笔），再以 **SillyTavern Lorebook 模式** 做精准上下文注入，实现高效、一致、可控的分段改写。

> 核心思路：**百万上下文用于「理解」而非「复读」** — 数据库即世界观，改写即迭代更新。

---

## 架构设计

```
用户上传小说 (.txt/.docx/.epub)
        │
        ▼
┌─────────────────────────┐
│  Phase 0: 预处理        │  ← FileLoader + ChapterSplitter ✅
│  格式清洗 / 章节识别     │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  Phase 1: 结构化提取    │  ← DeepSeekClient + Extractor ✅
│  角色/世界观/剧情/伏笔   │     百万上下文一次性提取
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  Phase 2: 混合数据库    │  ← SQLite + ChromaDB ✅
│  关系型 + 向量检索      │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  Phase 3: 分段改写引擎  │  ← Context Assembler ⏳
│  精准上下文注入          │     Rewrite Engine ⏳
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  Phase 4: Gradio Web UI │  ⏳
└─────────────────────────┘
```

---

## 项目状态

| 阶段 | 模块 | 状态 |
|------|------|:--:|
| Phase 0 | 文档预处理 (FileLoader + ChapterSplitter) | ✅ |
| Phase 1 | DeepSeek API 客户端 | ✅ |
| Phase 1 | 角色提取器 (CharacterExtractor) | ✅ |
| Phase 2 | SQLite 数据库模型 (6 表) | ✅ |
| Phase 2 | ChromaDB 向量存储 | ⏳ |
| Phase 3 | 上下文组装引擎 | ⏳ |
| Phase 3 | 改写引擎 | ⏳ |
| Phase 4 | Gradio Web UI | ⏳ |
| — | **总测试数: 37 passed** | ✅ |

---

## 快速开始

### 环境要求

- **Windows** (原生 Python，非 WSL)
- Python 3.11+
- DeepSeek API Key ([获取](https://platform.deepseek.com/))

### 安装

```powershell
# 克隆项目
git clone git@github.com:urushibararuka418/deep-reviser.git
cd deep-reviser

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 配置

```powershell
# 复制配置文件
copy .env.example .env

# 编辑 .env 填入 API Key
# DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 运行测试

```powershell
python -m pytest tests/ -v
# 期望: 37 passed
```

### 启动 Web UI (开发中)

```powershell
python -m src.ui.app
```

---

## 项目结构

```
deep-reviser/
├── src/
│   ├── config.py                 # 配置管理
│   ├── preprocessor/
│   │   ├── file_loader.py        # 多格式加载器 (.txt/.docx/.epub)
│   │   └── chapter_splitter.py   # 章节识别 + 段落分割
│   ├── extractor/
│   │   ├── ds_client.py          # DeepSeek API 封装
│   │   └── character_extractor.py # 角色结构化提取
│   ├── database/
│   │   ├── models.py             # SQLAlchemy ORM (6 表)
│   │   └── session.py            # 引擎/会话/init_db
│   ├── rewriter/                 # ⏳ 改写引擎
│   └── ui/                       # ⏳ Gradio 前端
├── tests/                        # pytest 测试套件 (37 tests)
├── .hermes/plans/                # 完整实施计划
├── requirements.txt
└── LICENSE                       # GPLv3
```

---

## 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.136 |
| 向量数据库 | ChromaDB | 1.5.8 |
| 关系数据库 | SQLite + SQLAlchemy | 2.0.49 |
| AI API | OpenAI SDK → DeepSeek | 2.33 |
| 前端 | Gradio | 6.13 |
| 文档解析 | python-docx + ebooklib | — |
| 中文分词 | jieba | 0.42 |
| 测试 | pytest | 9.0 |

---

## 核心理念

1. **百万上下文用于「理解」，不用「复读」** — 预处理时一次性提取结构化数据，改写时按需检索
2. **数据库即世界观** — 角色成长/伏笔回收后自动更新 DB，下次改写自动使用最新数据
3. **Lorebook 触发式注入** — 参照 SillyTavern World Info，只注入与当前段落相关的上下文
4. **一致性靠约束+校验** — 改写前注入约束，改写后二次校验，形成闭环

---

## 路线图

- [x] **Alpha**: 核心闭环 — 预处理 + 提取 + 数据库 (已完成)
- [ ] **Beta**: 向量检索 + 上下文组装 + 改写引擎
- [ ] **Gamma**: 高级功能 — 全局改文规划 / 伏笔追踪 / 多版本对比
- [ ] **Stable**: 打磨优化 — Gradio UI / 并行处理 / Token 成本统计

详见 [完整实施计划](.hermes/plans/2026-04-30-deep-reviser-mvp.md)

---

## 许可证

[GNU General Public License v3.0](LICENSE)

Copyright (C) 2026 Ruka
