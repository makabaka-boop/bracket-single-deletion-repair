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

单个赘余标记变体（repair_redundant）：装配宏偶尔多抄一个未确认标记，
额外允许删除至多一个未锁定位置，删除与替换各计一次修改。状态增加
一维 d ∈ {0, 1} 表示区间内是否已删除，被删位置的原稿下标随状态
携带，因此配对与改动清单都能回指原稿坐标，而不必事后猜测删了哪一位。
并列时先取修复串字典序最小，再取被删下标最小。
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

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


def repair_redundant(
    chars: Sequence[str], locked: Sequence[bool]
) -> Optional[Tuple[str, list, Optional[int]]]:
    """单个赘余标记修复：允许删除至多一个未锁定位置。

    删除与替换各计一次修改。奇数长度必须删除恰好一个位置；偶数长度
    删除一个位置后为奇数，不可能合法，因此结果与 repair() 完全一致。

    返回 (修复串, 配对下标, 被删下标或 None)；配对与删除下标一律为
    原稿零基坐标。并列时先取修复串字典序最小，再取被删下标最小。
    无解返回 None。
    """
    n = len(chars)
    if n == 0:
        return "", [], None

    # dp[d][i][j]：把区间 [i, j) 修复为合法串且区间内恰好删除 d 个位置
    # 的最优解 (cost, text, deleted)，不可达为 None。deleted 为被删位置
    # 的原稿下标（d=0 时为 -1）。是否已删除直接编码在状态里，原稿下标
    # 从不丢失。只有 d 与区间长度同奇偶的状态可达。
    dp = [[[None] * (n + 1) for _ in range(n + 1)] for _ in range(2)]
    for i in range(n + 1):
        dp[0][i][i] = (0, "", -1)

    for length in range(1, n + 1):
        d = length % 2
        for i in range(n + 1 - length):
            j = i + length
            best = None
            # 配对转移：位置 i 与 k 配成一对，删除（若 d=1）落在某一侧
            for k in range(i + 1, j):
                for dl in ((0, 1) if d else (0,)):
                    left = dp[dl][i + 1][k]
                    right = dp[d - dl][k + 1][j]
                    if left is None or right is None:
                        continue
                    base = left[0] + right[0]
                    inner, tail = left[1], right[1]
                    deleted = left[2] if dl else right[2]
                    for oc, cc in PAIRS:
                        if locked[i] and chars[i] != oc:
                            continue
                        if locked[k] and chars[k] != cc:
                            continue
                        cost = base + (chars[i] != oc) + (chars[k] != cc)
                        cand = (cost, oc + inner + cc + tail, deleted)
                        if best is None or cand < best:
                            best = cand
            if d:
                # 删除转移：直接删掉未锁定的 m（计 1 次），两侧各自平衡
                for m in range(i, j, 2):
                    if locked[m]:
                        continue
                    left = dp[0][i][m]
                    right = dp[0][m + 1][j]
                    if left is None or right is None:
                        continue
                    cand = (1 + left[0] + right[0], left[1] + right[1], m)
                    if best is None or cand < best:
                        best = cand
            dp[d][i][j] = best

    root = dp[n % 2][0][n]
    if root is None:
        return None
    _, text, deleted = root

    def to_orig(p: int) -> int:
        # 修复串坐标 -> 原稿坐标：跳过被删位置（单调映射，保序）
        return p + 1 if deleted >= 0 and p >= deleted else p

    # 依据修复结果重建配对下标（栈式扫描），再映射回原稿坐标
    pairs = []
    stack: list[int] = []
    for idx, ch in enumerate(text):
        if ch in OPEN_TO_CLOSE:
            stack.append(idx)
        else:
            pairs.append([to_orig(stack.pop()), to_orig(idx)])
    pairs.sort()

    return text, pairs, (deleted if deleted >= 0 else None)
