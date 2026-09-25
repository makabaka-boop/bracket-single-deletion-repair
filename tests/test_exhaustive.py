"""短串穷举/随机对拍：DP 结果必须与暴力枚举完全一致。"""

from __future__ import annotations

import itertools
import random

import pytest

from app.repair import OPEN_TO_CLOSE, repair
from tests.brute import brute_force

CHARS = "()[]{}"


def check_case(chars, locked):
    expected = brute_force(chars, locked)
    got = repair(chars, locked)
    if expected is None:
        assert got is None, f"{chars=} {locked=} 应无解，DP 给出 {got}"
        return
    exp_text, exp_cost = expected
    assert got is not None, f"{chars=} {locked=} 应有解 {exp_text}，DP 返回 None"
    text, pairs = got
    assert text == exp_text, (
        f"{''.join(chars)} {locked=} DP={text} 暴力={exp_text}"
    )
    # 修改数一致
    assert sum(a != b for a, b in zip(chars, text)) == exp_cost
    # 锁定位置未被改动
    for i, lk in enumerate(locked):
        if lk:
            assert text[i] == chars[i]
    # 配对结构核验：pairs 必须与栈式扫描一致
    stack = []
    derived = []
    for idx, ch in enumerate(text):
        if ch in OPEN_TO_CLOSE:
            stack.append(idx)
        else:
            assert stack, "闭括号多于开括号"
            o = stack.pop()
            assert OPEN_TO_CLOSE[text[o]] == ch, "括号类型不匹配"
            derived.append([o, idx])
    assert not stack
    assert pairs == sorted(derived)
    # pairs 恰好覆盖全部位置
    assert sorted(p for pair in pairs for p in pair) == list(range(len(chars)))


@pytest.mark.parametrize("n", [2, 4])
def test_exhaustive(n):
    """n=2: 144 种输入全枚举；n=4: 20736 种全枚举。"""
    for chars in itertools.product(CHARS, repeat=n):
        for locked in itertools.product([False, True], repeat=n):
            check_case(list(chars), list(locked))


@pytest.mark.parametrize("n,samples", [(6, 3000), (8, 1500)])
def test_random_sample(n, samples):
    rng = random.Random(20260923 + n)
    for _ in range(samples):
        chars = [rng.choice(CHARS) for _ in range(n)]
        locked = [rng.random() < 0.4 for _ in range(n)]
        check_case(chars, locked)


def test_random_biased_locked():
    """高锁定率随机样例，制造更多 NO_REPAIR 与受限情形。"""
    rng = random.Random(7)
    for _ in range(1500):
        n = rng.choice([2, 4, 6, 8])
        chars = [rng.choice(CHARS) for _ in range(n)]
        locked = [rng.random() < 0.75 for _ in range(n)]
        check_case(chars, locked)
