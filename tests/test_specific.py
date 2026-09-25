"""针对性场景：全锁定、交叉闭合、同成本多解取字典序最小、性能。"""

from __future__ import annotations

import random
import time

from app.repair import repair


def run(s, locked=None):
    n = len(s)
    locked = locked if locked is not None else [False] * n
    return repair(list(s), list(locked))


class TestAllLocked:
    def test_already_balanced(self):
        # 全锁定且已合法：零修改，原样返回
        text, pairs = run("({[]})", [True] * 6)
        assert text == "({[]})"
        assert pairs == [[0, 5], [1, 4], [2, 3]]

    def test_all_locked_invalid_no_repair(self):
        # 全锁定且不合法：NO_REPAIR，不得悄悄放宽锁定
        assert run("((", [True, True]) is None
        assert run("([)]", [True] * 4) is None
        assert run(")(", [True, True]) is None
        assert run("]]", [True, True]) is None

    def test_all_locked_valid_variants(self):
        text, pairs = run("()[]{}", [True] * 6)
        assert text == "()[]{}"
        assert pairs == [[0, 1], [2, 3], [4, 5]]


class TestCrossClosing:
    def test_cross_locked_ends(self):
        # "([)]" 首尾锁定 ('(' 与 ']')：0 无法与 3 配对（类型冲突），
        # 交叉闭合必须拆成 ()[] —— 改 2 处且唯一可行
        text, pairs = run("([)]", [True, False, False, True])
        assert text == "()[]"
        assert pairs == [[0, 1], [2, 3]]

    def test_cross_all_unlocked(self):
        # 无锁定时 "([)]"：(()) 与 ([]) 同为改 2 处，字典序取 "(())"
        text, pairs = run("([)]")
        assert text == "(())"
        assert pairs == [[0, 3], [1, 2]]

    def test_adjacent_swap(self):
        text, pairs = run(")(")
        assert text == "()"
        assert pairs == [[0, 1]]

    def test_mismatched_types_tie(self):
        # "(]"：改 () 与改 [] 成本同为 1，字典序取 "()"
        text, _ = run("(]")
        assert text == "()"


class TestTieBreaking:
    def test_all_opens_tie(self):
        # "(((("：(()) 与 ()() 同改 2 处；位置 1 上 '(' < ')'，故 "(())"
        text, pairs = run("((((")
        assert text == "(())"
        assert pairs == [[0, 3], [1, 2]]

    def test_two_closes(self):
        # "]]"：改成 "[]" 只需 1 处，优于改成 "()" 的 2 处
        text, _ = run("]]")
        assert text == "[]"

    def test_locked_open_forces_structure(self):
        # 位置 0 锁定 '['，其余自由；"[]{}" 与 "[{}]" 同为改 2 处，
        # 位置 1 上 ']' < '{'，故字典序取 "[]{}"
        text, pairs = run("[}}}", [True, False, False, False])
        assert text == "[]{}"
        assert pairs == [[0, 1], [2, 3]]

    def test_no_change_needed(self):
        text, pairs = run("{[()]}")
        assert text == "{[()]}"
        assert pairs == [[0, 5], [1, 4], [2, 3]]


class TestLockedPreserved:
    def test_locked_positions_untouched(self):
        s = "({[}])"
        locked = [True, False, True, False, False, True]
        out = run(s, locked)
        assert out is not None
        text, pairs = out
        for i, lk in enumerate(locked):
            if lk:
                assert text[i] == s[i]
        # 可逐位置核验的完整结构
        assert pairs == [[0, 5], [1, 4], [2, 3]]

    def test_locked_open_at_last_position_no_repair(self):
        # 末位锁定为开括号：任何合法串末位必是闭括号 => 无解
        assert run("((((((", [False] * 5 + [True]) is None

    def test_locked_close_at_first_position_no_repair(self):
        # 首位锁定为闭括号：任何合法串首位必是开括号 => 无解
        assert run("))))))", [True] + [False] * 5) is None


class TestPerformance:
    def test_max_length_random(self):
        rng = random.Random(160)
        chars = [rng.choice("()[]{}") for _ in range(160)]
        locked = [rng.random() < 0.3 for _ in range(160)]
        t0 = time.perf_counter()
        out = repair(chars, locked)
        elapsed = time.perf_counter() - t0
        assert elapsed < 5.0
        if out is not None:
            text, pairs = out
            assert len(text) == 160
            assert len(pairs) == 80

    def test_max_length_deep_nest_all_locked(self):
        # 全锁定的 80 对最深嵌套合法串，零修改快速判定
        opens = ("([{" * 27)[:80]
        close_map = {"(": ")", "[": "]", "{": "}"}
        s = opens + "".join(close_map[c] for c in reversed(opens))
        assert len(s) == 160
        text, pairs = run(s, [True] * 160)
        assert text == s
        assert len(pairs) == 80
