"""单个赘余标记修复的短串对拍。"""

from __future__ import annotations

import itertools
import random

import pytest

from app.repair import OPEN_TO_CLOSE, repair, repair_single_deletion
from tests.brute import all_balanced

CHARS = "()[]{}"


def brute_force_single_deletion(chars, locked):
    """枚举“不删除”或一个未锁定删除位，再枚举对应长度的合法串。"""
    n = len(chars)
    if n % 2 == 0:
        deletion_choices = [None]
    else:
        deletion_choices = [i for i, is_locked in enumerate(locked) if not is_locked]

    best = None
    for deleted_index in deletion_choices:
        kept = [i for i in range(n) if i != deleted_index]
        for target in all_balanced(len(kept)):
            cost = 0 if deleted_index is None else 1
            for original_index, target_char in zip(kept, target):
                before = chars[original_index]
                if before != target_char:
                    if locked[original_index]:
                        break
                    cost += 1
            else:
                candidate = (cost, target, deleted_index)
                if best is None or candidate < best:
                    best = candidate

    if best is None:
        return None
    return best


def check_single_deletion(chars, locked):
    expected = brute_force_single_deletion(chars, locked)
    got = repair_single_deletion(chars, locked)

    if expected is None:
        assert got is None, f"{chars=} {locked=} 应无解，求解器给出 {got}"
        return

    exp_cost, exp_text, exp_deleted = expected
    assert got is not None, f"{chars=} {locked=} 应有解，求解器返回 None"
    assert got.text == exp_text, f"{chars=} {locked=} {got=} {expected=}"
    assert got.deleted_index == exp_deleted, f"{chars=} {locked=} {got=} {expected=}"

    replacement_count = sum(before != after for _, before, after in got.changes)
    assert replacement_count + (got.deleted_index is not None) == exp_cost

    # changes 只包含替换，且全部回指原稿中的未锁定位置。
    change_indexes = set()
    for index, before, after in got.changes:
        assert 0 <= index < len(chars)
        assert not locked[index]
        assert before == chars[index]
        assert before != after
        change_indexes.add(index)

    kept = set(range(len(chars)))
    if got.deleted_index is not None:
        assert not locked[got.deleted_index]
        kept.remove(got.deleted_index)
        assert got.deleted_index not in change_indexes

    # 修复串长度与原稿保留位置数一致。
    assert len(got.text) == len(kept)

    # pairs 使用原稿零基坐标，并恰好覆盖保留位置。
    assert sorted(position for pair in got.pairs for position in pair) == sorted(kept)
    stack = []
    by_open = {}
    for output_index, original_index in enumerate(sorted(kept)):
        ch = got.text[output_index]
        if ch in OPEN_TO_CLOSE:
            stack.append(original_index)
            by_open[original_index] = ch
        else:
            assert stack
            open_index = stack.pop()
            assert OPEN_TO_CLOSE[by_open[open_index]] == ch
            assert [open_index, original_index] in got.pairs
    assert not stack


@pytest.mark.parametrize("n", [3, 4])
def test_exhaustive_short_single_deletion(n):
    """n=3 覆盖全部删除/替换裁决；n=4 覆盖偶数时与原修复器的一致性。"""
    for chars in itertools.product(CHARS, repeat=n):
        for locked in itertools.product([False, True], repeat=n):
            chars = list(chars)
            locked = list(locked)
            check_single_deletion(chars, locked)

            if n % 2 == 0:
                ordinary = repair(chars, locked)
                single = repair_single_deletion(chars, locked)
                if ordinary is None:
                    assert single is None
                else:
                    assert single is not None
                    assert single.text == ordinary[0]
                    assert single.pairs == ordinary[1]
                    assert single.deleted_index is None


@pytest.mark.parametrize("n,samples", [(5, 2000), (6, 1000), (7, 500), (8, 500)])
def test_random_single_deletion(n, samples):
    rng = random.Random(20260925 + n)
    for _ in range(samples):
        chars = [rng.choice(CHARS) for _ in range(n)]
        locked = [rng.random() < 0.45 for _ in range(n)]
        check_single_deletion(chars, locked)


def test_same_repaired_string_prefers_smaller_deleted_index():
    # 删除 0 或 2 都得到已锁定的 "()"，并列时 deletedIndex 必须取 0。
    out = repair_single_deletion(["(", "(", ")"], [False, True, True])
    assert out.text == "()"
    assert out.pairs == [[1, 2]]
    assert out.deleted_index == 0
    assert out.changes == []

    # 删除 1 或 2 都得到已锁定的 "()"，并列时 deletedIndex 必须取 1。
    out = repair_single_deletion(["(", ")", ")"], [True, False, False])
    assert out.text == "()"
    assert out.pairs == [[0, 2]]
    assert out.deleted_index == 1
    assert out.changes == []


def test_repaired_string_order_beats_deleted_index():
    # 删除位置 0 得 "()"；保留位置 0 则只能改为较后的字典序结果。
    out = repair_single_deletion(["[", "(", ")"], [False, False, True])
    assert out.text == "()"
    assert out.pairs == [[1, 2]]
    assert out.deleted_index == 0
    assert out.changes == []


def test_locked_position_cannot_be_deleted():
    # 赘余的位置 1 被锁定；删除未锁定位置 2，并将位置 0 替换为 '('。
    out = repair_single_deletion(["[", ")", "]"], [False, True, False])
    assert out.text == "()"
    assert out.pairs == [[0, 1]]
    assert out.deleted_index == 2
    assert out.changes == [(0, "[", "(")]


def test_all_locked_invalid_odd_has_no_deletable_position():
    assert repair_single_deletion(list("((("), [True] * 3) is None


def test_lock_conflict_returns_no_repair_without_partial_pairs():
    # 可删任意未锁定位置，但剩余两个锁定字符永远不能成为一对。
    assert repair_single_deletion(["(", "[", "{"], [True, True, False]) is None
