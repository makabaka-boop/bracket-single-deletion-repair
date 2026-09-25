"""对拍用暴力求解器：枚举全部合法括号串，取 (修改数, 字典序) 最小者。

合法串总数为 Catalan(n/2) * 3^(n/2)，n=8 时为 7056，n=10 时为 98034，
仅用于短串对拍。

brute_force_redundant：单个赘余标记变体，额外枚举被删除的位置，
按 (修改数, 修复串字典序, 被删下标) 取最优。
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


def brute_force_redundant(
    chars: Sequence[str], locked: Sequence[bool]
) -> Optional[Tuple[str, int, Optional[int]]]:
    """删除至多一个位置的暴力解：返回 (修复串, 修改数, 被删下标或 None)。

    奇数长度必须删除恰好一个未锁定位置；偶数长度删除一个后为奇数，
    不可能合法，只允许不删。并列先取修复串字典序最小，再取被删下标
    最小。无解返回 None。
    """
    n = len(chars)
    best: Optional[Tuple[int, str, int]] = None
    deletions = (-1,) if n % 2 == 0 else range(n)
    for m in deletions:
        if m >= 0 and locked[m]:
            continue
        kept = [i for i in range(n) if i != m]
        for target in all_balanced(len(kept)):
            cost = 0
            feasible = True
            for p, i in enumerate(kept):
                if target[p] != chars[i]:
                    if locked[i]:
                        feasible = False
                        break
                    cost += 1
            if not feasible:
                continue
            cand = (cost + (m >= 0), target, m)
            if best is None or cand < best:
                best = cand
    if best is None:
        return None
    cost, text, m = best
    return text, cost, (m if m >= 0 else None)
