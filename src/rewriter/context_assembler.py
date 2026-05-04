"""上下文组装引擎。"""

from dataclasses import dataclass


@dataclass
class Context:
    """改写时使用的上下文容器。"""

    character_context: str = ""
    lorebook_context: str = ""
    similar_context: str = ""


class ContextAssembler:
    """根据当前段落命中角色、设定与相似片段。"""

    def assemble(self, segment_text, characters=None, lore_entries=None, similar_segments=None):
        """组装用于改写的结构化上下文。"""
        characters = characters or []
        lore_entries = lore_entries or []
        similar_segments = similar_segments or []

        return Context(
            character_context=self._build_character_context(segment_text, characters),
            lorebook_context=self._build_lore_context(segment_text, lore_entries),
            similar_context=self._build_similar_context(similar_segments),
        )

    def _build_character_context(self, segment_text, characters):
        """根据名字或别名命中角色资料。"""
        matched_lines = []
        for character in characters:
            keywords = [character.get("name", ""), *character.get("aliases", [])]
            if not self._matches_any_keyword(segment_text, keywords):
                continue

            matched_lines.append(self._format_character(character))

        return "\n".join(self._deduplicate(matched_lines))

    def _build_lore_context(self, segment_text, lore_entries):
        """根据名称或关键词命中设定资料。"""
        matched_lines = []
        for entry in lore_entries:
            keywords = [entry.get("name", ""), *entry.get("keywords", [])]
            if not self._matches_any_keyword(segment_text, keywords):
                continue

            matched_lines.append(self._format_lore(entry))

        return "\n".join(self._deduplicate(matched_lines))

    def _build_similar_context(self, similar_segments):
        """拼接相似片段内容。"""
        lines = []
        for segment in similar_segments:
            if isinstance(segment, dict):
                text = segment.get("text", "")
            else:
                text = str(segment)

            if text:
                lines.append(text)

        return "\n".join(self._deduplicate(lines))

    @staticmethod
    def _matches_any_keyword(segment_text, keywords):
        """只要段落中出现任一关键词，即视为命中。"""
        return any(keyword and keyword in segment_text for keyword in keywords)

    @staticmethod
    def _format_character(character):
        """格式化角色上下文。"""
        parts = [character.get("name", "")]

        aliases = character.get("aliases", [])
        if aliases:
            parts.append(f"别名：{'/'.join(aliases)}")

        if character.get("role_type"):
            parts.append(f"身份：{character['role_type']}")

        traits = character.get("personality_traits", [])
        if traits:
            parts.append(f"性格：{'/'.join(traits)}")

        abilities = character.get("abilities", [])
        if abilities:
            parts.append(f"能力：{'/'.join(abilities)}")

        return "；".join(part for part in parts if part)

    @staticmethod
    def _format_lore(entry):
        """格式化设定上下文。"""
        parts = []

        if entry.get("category"):
            parts.append(f"类别：{entry['category']}")

        if entry.get("name"):
            parts.append(entry["name"])

        keywords = entry.get("keywords", [])
        if keywords:
            parts.append(f"关键词：{'/'.join(keywords)}")

        if entry.get("description"):
            parts.append(f"说明：{entry['description']}")

        return "；".join(parts)

    @staticmethod
    def _deduplicate(lines):
        """保持原顺序去重，避免重复上下文。"""
        seen = set()
        result = []
        for line in lines:
            if line in seen:
                continue
            seen.add(line)
            result.append(line)
        return result
