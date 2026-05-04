"""世界设定提取器 — 从小说全文中提取可复用的世界观设定信息"""

from src.extractor.ds_client import DeepSeekClient

# 世界设定提取提示词 — 引导 DeepSeek 模型输出结构化的 Lore 条目

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
    """世界设定提取器 — 封装 DeepSeekClient，从全文中抽取可检索的设定条目。

    使用方式:
        extractor = LoreExtractor()          # 使用默认 DeepSeekClient
        extractor = LoreExtractor(client=my_client)  # 注入自定义 client（便于测试）
        result = extractor.extract(full_text)        # 返回 {"entries": [...]}

    result["entries"] 中每个条目包含: category, name, keywords, description, first_chapter
    """

    def __init__(self, client=None):
        """初始化世界设定提取器。

        Args:
            client: 可选，注入 DeepSeekClient 实例（便于单元测试 mock），
                    不传则自动创建默认实例。
        """
        self.client = client or DeepSeekClient()

    def extract(self, full_text: str) -> dict:
        """从小说全文中提取世界设定。

        Args:
            full_text: 小说完整文本

        Returns:
            {"entries": [...]} 格式的字典，entries 列表中每个元素
            为一个结构化世界设定条目字典。
        """
        return self.client.extract_json(LORE_EXTRACTION_PROMPT, full_text)
