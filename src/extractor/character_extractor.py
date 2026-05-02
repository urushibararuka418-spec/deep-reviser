"""角色提取器 — 从小说全文中提取所有角色信息"""
from src.extractor.ds_client import DeepSeekClient

# 角色提取提示词 — 引导 DeepSeek 模型以结构化 JSON 输出角色信息
CHARACTER_EXTRACTION_PROMPT = """你是一位专业的小说分析助手。请从以下小说全文中提取所有角色信息。

对每个角色提取以下字段：
- name: 角色姓名
- aliases: 别名列表（如昵称、称号、化名等）
- role_type: 角色类型（如 主角、配角、反派、路人 等）
- personality_traits: 性格特征列表
- abilities: 能力/技能列表（如 武功、法术、特殊能力等）
- relationships: 角色关系列表，每项包含 target（目标角色名）、relation（关系类型）、description（关系描述）
- character_arc: 角色成长弧线/发展轨迹简述
- first_appearance: 首次出场位置（章节/场景）
- quote_examples: 代表性台词/引语列表

以严格 JSON 格式输出：{"characters": [...]}"""


class CharacterExtractor:
    """角色提取器 — 封装 DeepSeekClient，从小说全文中提取结构化角色信息。

    使用方式:
        extractor = CharacterExtractor()          # 使用默认 DeepSeekClient
        extractor = CharacterExtractor(client=my_client)  # 注入自定义 client（便于测试）
        result = extractor.extract(full_text)     # 返回 {"characters": [...]}

    result["characters"] 中每个角色包含: name, aliases, role_type, personality_traits,
    abilities, relationships, character_arc, first_appearance, quote_examples
    """

    def __init__(self, client=None):
        """初始化角色提取器。

        Args:
            client: 可选，注入 DeepSeekClient 实例（便于单元测试 mock），
                    不传则自动创建默认实例。
        """
        self.client = client or DeepSeekClient()

    def extract(self, full_text: str) -> dict:
        """从小说全文中提取所有角色信息。

        Args:
            full_text: 小说完整文本

        Returns:
            {"characters": [...]} 格式的字典，characters 列表中每个元素
            为一个角色的结构化信息字典。
        """
        return self.client.extract_json(CHARACTER_EXTRACTION_PROMPT, full_text)
