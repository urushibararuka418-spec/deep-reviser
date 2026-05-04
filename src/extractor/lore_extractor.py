"""世界设定提取器（Lorebook 模式）"""

from src.extractor.ds_client import DeepSeekClient

LORE_EXTRACTION_PROMPT = """你是一位专业的小说世界观分析助手。请从以下小说全文中提取可复用的世界设定（Lore）信息。

对每个设定条目提取以下字段：
- category: 设定类别（如 地理、组织、历史、制度、种族、神话、器物、修炼体系 等）
- name: 设定名称
- keywords: 相关关键词列表，便于后续检索和召回
- description: 对该设定的简洁说明，概括其核心信息与作用
- first_chapter: 该设定首次被明确提及的章节/位置

要求：
1. 只提取对理解剧情或世界构成有意义的设定，不要输出普通场景细节。
2. 若文本中没有明确设定，可返回空列表。
3. 关键词应尽量简短，避免重复。

以严格 JSON 格式输出：{"entries": [{"category": "", "name": "", "keywords": [], "description": "", "first_chapter": ""}]}"""


class LoreExtractor:
    """世界设定提取器。"""

    def __init__(self, client=None):
        """初始化提取器，可注入自定义 client 以便测试。"""
        self.client = client or DeepSeekClient()

    def extract(self, full_text: str) -> dict:
        """从小说全文中提取世界设定，返回 {"entries": [...]}。"""
        return self.client.extract_json(LORE_EXTRACTION_PROMPT, full_text)
