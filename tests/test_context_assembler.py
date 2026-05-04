"""ContextAssembler 测试套件。"""

from src.rewriter.context_assembler import Context, ContextAssembler


def test_assemble_returns_empty_context_when_no_sources_match():
    """没有任何匹配时，应返回空上下文。"""
    assembler = ContextAssembler()

    result = assembler.assemble("这是一段普通叙述。")

    assert result == Context(character_context="", lorebook_context="", similar_context="")


def test_assemble_matches_character_by_name():
    """应根据段落中的角色名匹配角色信息。"""
    assembler = ContextAssembler()
    characters = [
        {
            "name": "李明",
            "role_type": "主角",
            "personality_traits": ["冷静", "执拗"],
            "abilities": ["剑术"],
        }
    ]

    result = assembler.assemble("李明握紧长剑，站在雨中。", characters=characters)

    assert "李明" in result.character_context
    assert "主角" in result.character_context
    assert "冷静" in result.character_context


def test_assemble_matches_character_by_alias():
    """应支持根据角色别名匹配角色信息。"""
    assembler = ContextAssembler()
    characters = [
        {
            "name": "苏瑶",
            "aliases": ["阿瑶"],
            "role_type": "女主",
        }
    ]

    result = assembler.assemble("阿瑶推门而入，神色凝重。", characters=characters)

    assert "苏瑶" in result.character_context
    assert "阿瑶" in result.character_context


def test_assemble_matches_lore_by_name_and_keywords():
    """应根据设定名称和关键词匹配世界设定。"""
    assembler = ContextAssembler()
    lore_entries = [
        {
            "category": "组织",
            "name": "青云宗",
            "keywords": ["剑修", "宗门"],
            "description": "东州最强宗门之一。",
        }
    ]

    result = assembler.assemble("青云宗的剑修弟子已经封锁山门。", lore_entries=lore_entries)

    assert "青云宗" in result.lorebook_context
    assert "剑修" in result.lorebook_context
    assert "东州最强宗门之一" in result.lorebook_context


def test_assemble_collects_multiple_similar_segments():
    """应拼接相似片段上下文。"""
    assembler = ContextAssembler()
    similar_segments = [
        "前文一：李明曾在雨夜练剑。",
        {"text": "前文二：青云宗戒备森严。"},
    ]

    result = assembler.assemble("新的段落", similar_segments=similar_segments)

    assert "前文一：李明曾在雨夜练剑。" in result.similar_context
    assert "前文二：青云宗戒备森严。" in result.similar_context


def test_assemble_deduplicates_repeated_matches():
    """同一角色和设定被多次命中时，不应重复输出。"""
    assembler = ContextAssembler()
    characters = [{"name": "李明", "aliases": ["小明"], "role_type": "主角"}]
    lore_entries = [{"category": "地点", "name": "黑水城", "keywords": ["边城"], "description": "边境要塞。"}]

    result = assembler.assemble(
        "李明看着小明留下的旧剑，准备进入黑水城。黑水城的风雪越来越大。",
        characters=characters,
        lore_entries=lore_entries,
    )

    assert result.character_context.count("李明") == 1
    assert result.lorebook_context.count("黑水城") == 1
