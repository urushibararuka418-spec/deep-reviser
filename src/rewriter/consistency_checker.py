"""一致性校验器。"""


class ConsistencyChecker:
    """检查改写前后角色与设定是否一致。"""

    def check(self, original, rewritten, characters=None, settings=None):
        """返回一致性检查结果。"""
        characters = characters or []
        settings = settings or []
        issues = []

        issues.extend(self._check_characters(original, rewritten, characters))
        issues.extend(self._check_settings(original, rewritten, settings))

        return {"consistent": not issues, "issues": issues}

    def _check_characters(self, original, rewritten, characters):
        """检查原文角色是否保留，以及是否凭空新增角色。"""
        issues = []

        for character in characters:
            name = character.get("name", "")
            aliases = character.get("aliases", [])
            original_hit = self._contains_any(original, [name, *aliases])
            rewritten_hit = self._contains_any(rewritten, [name, *aliases])

            if original_hit and not rewritten_hit:
                issues.append(f"角色不一致：原文中的角色“{name}”在改写后消失。")

            if not original_hit and name and name in rewritten:
                issues.append(f"角色不一致：改写中新增了原文未出现的角色“{name}”。")

        return issues

    def _check_settings(self, original, rewritten, settings):
        """检查原文命中的设定是否在改写后被替换或丢失。"""
        issues = []

        for setting in settings:
            name = setting.get("name", "")
            keywords = setting.get("keywords", [])
            original_hit = self._contains_any(original, [name, *keywords])
            rewritten_hit = self._contains_any(rewritten, [name, *keywords])

            if original_hit and not rewritten_hit:
                issues.append(f"设定冲突：原文中的设定“{name}”未在改写后保留。")

        return issues

    @staticmethod
    def _contains_any(text, keywords):
        """只要文本命中任一关键词即返回 True。"""
        return any(keyword and keyword in text for keyword in keywords)
