"""ConsistencyChecker 测试套件。"""

from src.rewriter.consistency_checker import ConsistencyChecker


def test_check_returns_consistent_when_no_issues_found():
    """角色和设定都一致时，应返回通过。"""
    checker = ConsistencyChecker()
    characters = [{"name": "李明"}, {"name": "苏瑶", "aliases": ["阿瑶"]}]
    settings = [{"name": "青云宗", "keywords": ["剑修"]}]

    result = checker.check(
        "李明和阿瑶回到青云宗，商议剑修试炼。",
        "李明与苏瑶回到青云宗，继续准备剑修试炼。",
        characters=characters,
        settings=settings,
    )

    assert result == {"consistent": True, "issues": []}


def test_check_flags_missing_character_name():
    """原文出现的角色在改写后消失时，应报告问题。"""
    checker = ConsistencyChecker()

    result = checker.check(
        "李明看着窗外的雨。",
        "少年看着窗外的雨。",
        characters=[{"name": "李明"}],
    )

    assert result["consistent"] is False
    assert any("李明" in issue for issue in result["issues"])


def test_check_flags_unexpected_new_character_name():
    """改写中新增未在原文出现的角色名时，应报告问题。"""
    checker = ConsistencyChecker()

    result = checker.check(
        "李明独自下山。",
        "李明和张伟一起下山。",
        characters=[{"name": "李明"}, {"name": "张伟"}],
    )

    assert result["consistent"] is False
    assert any("张伟" in issue for issue in result["issues"])


def test_check_flags_setting_conflict_when_original_setting_is_missing():
    """原文命中的设定在改写后缺失时，应视为设定冲突。"""
    checker = ConsistencyChecker()
    settings = [{"name": "青云宗", "keywords": ["宗门", "剑修"]}]

    result = checker.check(
        "李明回到青云宗宗门，准备参加剑修试炼。",
        "李明回到赤焰谷，准备参加火修试炼。",
        settings=settings,
    )

    assert result["consistent"] is False
    assert any("青云宗" in issue for issue in result["issues"])
