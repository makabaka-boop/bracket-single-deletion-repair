"""对拍用暴力求解器：枚举全部合法括号串，取 (修改数, 字典序) 最小者。

合法串总数为 Catalan(n/2) * 3^(n/2)，n=8 时为 7056，n=10 时为 98034，
仅用于短串对拍。
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Sequence, Tuple

OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}


@lru_cache(maxsize=None)
def all_balanced(n: int) -> Tuple[str, ...]:
    """生成长度为 n 的全部合法括号串（字典序升序）。"""
    out: List[str] = []

    def dfs(buf: List[str], stack: List[str]) -> None:
        if len(buf) == n:
            out.append("".join(buf))
            return
        # 剩余位置必须够关闭当前栈，才允许再开新括号
        if len(buf) + len(stack) < n:
            for oc, cc in OPEN_TO_CLOSE.items():
                buf.append(oc)
                stack.append(cc)
                dfs(buf, stack)
                stack.pop()
                buf.pop()
        if stack:
            buf.append(stack.pop())
            dfs(buf, stack)
            stack.append(buf.pop())

    dfs([], [])
    return tuple(out)


def brute_force(
    chars: Sequence[str], locked: Sequence[bool]
) -> Optional[Tuple[str, int]]:
    """返回 (最优修复串, 修改数)，无解返回 None。"""
    n = len(chars)
    best: Optional[Tuple[str, int]] = None
    for target in all_balanced(n):
        cost = 0
        feasible = True
        for i, ch in enumerate(target):
            if ch != chars[i]:
                if locked[i]:
                    feasible = False
                    break
                cost += 1
        if not feasible:
            continue
        if best is None or cost < best[1] or (cost == best[1] and target < best[0]):
            best = (target, cost)
    return best
