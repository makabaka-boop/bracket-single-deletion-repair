"""区间动态规划修复括号宏。

问题：给定 2..160 个偶数长度 token，每个位置有一个字符（()[]{} 之一）和
locked 标记。只允许修改未锁定位置的字符，使整串成为类型正确的平衡嵌套
序列。目标：先最小化修改数，再按 '(' ')' '[' ']' '{' '}' 的顺序取字典序
最小结果。无解返回 None。

做法：经典区间 DP。dp[i][j] 表示把区间 [i, j) 修复为合法括号序列的
(最小修改数, 字典序最小结果串)。长度为偶数的区间才有意义。

转移（len >= 2）：
  对 k = i+1, i+3, ..., j-1（步长 2）：
    若 [i+1, k) 与 [k+1, j) 均可修复，则枚举位置 i 的开括号 oc 与位置 k
    的匹配闭括号 cc（受 locked 约束），候选为：
        cost = (oc != s[i]) + (cc != s[k]) + cost(i+1,k) + cost(k+1,j)
        text = oc + text(i+1,k) + cc + text(k+1,j)
  取 (cost, text) 最小者。

注意：字典序比较基于 ASCII，而 '('=40 ')'=41 '['=91 ']'=93 '{'=123 '}'=125
恰好与要求的顺序一致，因此直接比较字符串即可。

复杂度：状态 O(n^2)，每状态转移 O(n)，总 O(n^3)。n=160 时约 8.7 万个
候选串拼接，毫秒级完成。
"""

from __future__ import annotations

from typing import List, NamedTuple, Optional, Sequence, Tuple

OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
PAIRS = (("(", ")"), ("[", "]"), ("{", "}"))

# (cost, text)；cost 为 None 表示该区间不可修复
State = Tuple[Optional[int], Optional[str]]


def repair(chars: Sequence[str], locked: Sequence[bool]) -> Optional[Tuple[str, list]]:
    """修复括号序列。

    返回 (修复后的串, 配对下标列表)。配对列表按开括号下标升序给出
    [open_index, close_index]。不可修复时返回 None。
    """
    n = len(chars)
    if n == 0:
        return "", []
    if n % 2 != 0:
        return None

    INF: State = (None, None)
    # dp[i][j] 仅对偶数长度区间有效
    dp = [[INF] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][i] = (0, "")

    for length in range(2, n + 1, 2):
        for i in range(n + 1 - length):
            j = i + length
            best: State = INF
            for k in range(i + 1, j, 2):
                left = dp[i + 1][k]
                right = dp[k + 1][j]
                if left[0] is None or right[0] is None:
                    continue
                base = left[0] + right[0]
                inner = left[1]
                tail = right[1]
                for oc, cc in PAIRS:
                    if locked[i] and chars[i] != oc:
                        continue
                    if locked[k] and chars[k] != cc:
                        continue
                    cost = base + (chars[i] != oc) + (chars[k] != cc)
                    text = oc + inner + cc + tail
                    if best[0] is None or cost < best[0] or (
                        cost == best[0] and text < best[1]
                    ):
                        best = (cost, text)
            dp[i][j] = best

    if dp[0][n][0] is None:
        return None

    result = dp[0][n][1]

    # 依据修复结果重建配对下标（栈式扫描，与 DP 结构一致）
    pairs = []
    stack: list[int] = []
    for idx, ch in enumerate(result):
        if ch in OPEN_TO_CLOSE:
            stack.append(idx)
        else:
            pairs.append([stack.pop(), idx])
    pairs.sort()

    return result, pairs


class SingleDeletionResult(NamedTuple):
    """单个赘余标记修复结果，所有坐标均为原稿零基下标。"""

    text: str
    pairs: List[List[int]]
    # (index, before, after)，只包含替换，不包含删除。
    changes: List[Tuple[int, str, str]]
    deleted_index: Optional[int]


class _DeletionState(NamedTuple):
    cost: int
    text: str
    # 修复串中每个字符对应的原稿位置；删除位置不会出现在这里。
    positions: Tuple[int, ...]
    deleted_index: Optional[int]


def repair_single_deletion(
    chars: Sequence[str], locked: Sequence[bool]
) -> Optional[SingleDeletionResult]:
    """至多删除一个未锁定位置，其余未锁定位置可替换。

    奇数长度必须恰好删除一个位置；偶数长度删除一个后会成为奇数，不可能合法，
    因此不使用删除，结果应与 ``repair`` 一致。

    状态 ``dp[used][i][j]`` 表示原稿区间 [i, j) 在是否已用掉删除次数
    （``used`` 为 0/1）后修复成合法串的最优状态。状态始终携带原稿坐标和
    deleted_index，而不是先删掉字符再对缩短后的数组重新编号。
    """
    n = len(chars)
    if not 3 <= n <= 81:
        raise ValueError("single-deletion repair requires 3..81 tokens")

    need_delete = n % 2
    dp: List[List[List[Optional[_DeletionState]]]] = [
        [[None] * (n + 1) for _ in range(n + 1)] for _ in range(2)
    ]
    for i in range(n + 1):
        dp[0][i][i] = _DeletionState(0, "", (), None)

    def better(current: Optional[_DeletionState], candidate: _DeletionState) -> bool:
        return (
            current is None
            or candidate.cost < current.cost
            or (
                candidate.cost == current.cost
                and (candidate.text, candidate.deleted_index)
                < (current.text, current.deleted_index)
            )
        )

    for length in range(1, n + 1):
        for i in range(n + 1 - length):
            j = i + length

            for used in (0, 1):
                # 合法括号串长度必须为偶数：length - used 为保留字符数。
                if length < used or (length - used) % 2 != 0:
                    continue

                best: Optional[_DeletionState] = None

                # 直接删除区间首个原稿位置。删除权使用后，其余部分不能再删。
                if used == 1 and not locked[i]:
                    child = dp[0][i + 1][j]
                    if child is not None:
                        candidate = _DeletionState(
                            child.cost + 1,
                            child.text,
                            child.positions,
                            i,
                        )
                        if better(best, candidate):
                            best = candidate

                # 保留原稿位置 i 作为开括号，并枚举它在原稿中的闭括号 k。
                for k in range(i + 1, j):
                    if used == 0:
                        child_pairs = (
                            (dp[0][i + 1][k], dp[0][k + 1][j]),
                        )
                    else:
                        child_pairs = (
                            (dp[1][i + 1][k], dp[0][k + 1][j]),
                            (dp[0][i + 1][k], dp[1][k + 1][j]),
                        )

                    for inner, tail in child_pairs:
                        if inner is None or tail is None:
                            continue

                        base_cost = inner.cost + tail.cost
                        deleted_index = (
                            inner.deleted_index
                            if inner.deleted_index is not None
                            else tail.deleted_index
                        )
                        for oc, cc in PAIRS:
                            if locked[i] and chars[i] != oc:
                                continue
                            if locked[k] and chars[k] != cc:
                                continue

                            candidate = _DeletionState(
                                base_cost
                                + (chars[i] != oc)
                                + (chars[k] != cc),
                                oc + inner.text + cc + tail.text,
                                (i,) + inner.positions + (k,) + tail.positions,
                                deleted_index,
                            )
                            if better(best, candidate):
                                best = candidate

                dp[used][i][j] = best

    state = dp[need_delete][0][n]
    if state is None:
        return None

    pairs: List[List[int]] = []
    stack: List[int] = []
    for output_index, original_index in enumerate(state.positions):
        ch = state.text[output_index]
        if ch in OPEN_TO_CLOSE:
            stack.append(original_index)
        else:
            pairs.append([stack.pop(), original_index])
    pairs.sort()

    changes: List[Tuple[int, str, str]] = []
    for output_index, original_index in enumerate(state.positions):
        before = chars[original_index]
        after = state.text[output_index]
        if before != after:
            changes.append((original_index, before, after))
    changes.sort()

    return SingleDeletionResult(
        state.text,
        pairs,
        changes,
        state.deleted_index,
    )
