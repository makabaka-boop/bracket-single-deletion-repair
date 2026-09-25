# 宏修复 API（Macro Repair）

自动装配机的工艺宏用三种成对括号 `()`、`[]`、`{}` 表示嵌套步骤。本服务对
抄录错误（开始/结束标记颠倒、类型错配等）进行**最小代价修复**：仅允许改动
人工未确认（`locked=false`）的位置。

此外提供**单个赘余标记修复**入口：装配宏偶尔多抄一个未确认标记时，允许
删除至多一个 `locked=false` 的位置（删除与替换各计一次修改），并明确指出
删掉的究竟是原稿哪一位。

## 规则

1. 输入为 2..160 个、偶数个 token（`/repair-redundant` 为 3..81 个、
   奇偶均可）；每项只有两个字段：
   - `char`：只能是 `(`、`)`、`[`、`]`、`{`、`}` 之一；
   - `locked`：严格布尔值。
   额外字段、类型错误、`/repair` 的奇数长度均返回 `422`。
2. 只允许修改 `locked=false` 的位置；锁定内容不会被放宽。
3. 优化目标：先最小化修改数，再按 `(` `)` `[` `]` `{` `}` 的顺序取
   字典序最小的结果（该顺序与 ASCII 码序一致）。`/repair-redundant`
   在此基础上再取被删除的原稿零基下标最小者。
4. 不存在可行方案时返回 `NO_REPAIR`。

## 运行

```bash
docker compose up --build
# 服务位于 http://localhost:8000 ，文档 /docs
```

本地开发：

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

## 接口

`POST /repair`

```json
{
  "tokens": [
    {"char": "(", "locked": true},
    {"char": "[", "locked": false},
    {"char": ")", "locked": false},
    {"char": "]", "locked": true}
  ]
}
```

成功：

```json
{
  "status": "OK",
  "repaired": "()[]",
  "pairs": [[0, 1], [2, 3]],
  "changes": [
    {"index": 1, "before": "[", "after": ")"},
    {"index": 2, "before": ")", "after": "["}
  ]
}
```

- `pairs`：配对下标 `[open_index, close_index]`，按开括号下标升序，
  0 基，覆盖全部位置，可逐位置核验。
- `changes`：每项改动的下标及改动前后字符；锁定位置不会出现。

无解：

```json
{"status": "NO_REPAIR", "repaired": null, "pairs": null, "changes": null}
```

`POST /repair-redundant`（单个赘余标记修复，3..81 个 token）

```json
{
  "tokens": [
    {"char": "(", "locked": false},
    {"char": "]", "locked": false},
    {"char": ")", "locked": false}
  ]
}
```

成功：

```json
{
  "status": "OK",
  "repaired": "()",
  "pairs": [[0, 2]],
  "changes": [],
  "deletedIndex": 1
}
```

- 仅允许删除至多一个 `locked=false` 的位置，删除与替换各计一次修改；
  奇数长度必须删除恰好一个位置。
- `deletedIndex`：被删除位置的原稿零基下标；偶数长度无需删除时为
  `null`，此时结果与 `/repair` 完全一致。
- `pairs`、`changes` 一律回指原稿坐标；被删位置不出现在 `changes` 中，
  仅以 `deletedIndex` 单独列出。
- 并列时先取修复串字典序最小，再取 `deletedIndex` 最小。

无解：

```json
{"status": "NO_REPAIR", "repaired": null, "pairs": null, "changes": null, "deletedIndex": null}
```

## 算法（区间 DP）

`app/repair.py` 中 `dp[i][j]` 记录把区间 `[i, j)` 修复为合法序列的
`(最小修改数, 字典序最小串)`：

- 空区间代价为 0；
- 枚举与位置 `i` 配对的 `k`（步长 2，保证两个子区间均为偶数长度），
  再枚举三种括号对（受 `locked` 约束），合并子区间结果；
- 转移按 `(cost, text)` 取最小；无解状态标记为不可达。

状态数 O(n²)、每状态 O(n) 次转移，总复杂度 O(n³)；n=160 实测约 0.3s。
配对下标由修复结果用栈重建。

`repair_redundant` 在同一框架上把"区间内是否已删除"编码进状态：
`dp[d][i][j]`（d ∈ {0,1}）记录恰好删除 d 个位置的最优解
`(cost, text, deleted)`，被删位置的原稿下标随状态携带，因此配对与
改动清单都能回指原稿坐标。转移分两种：位置 `i` 与 `k` 配对、删除落在
某一侧子区间；或直接删掉未锁定的 `m`、两侧各自平衡。裁决键为
`(修改数, 修复串, 被删下标)` 的字典序。偶数长度时删除一个位置必得
奇数长度、不可能合法，结果与 `repair` 完全一致。

## 测试

`tests/` 包含：

- `test_exhaustive.py`：n=2、n=4 对全部输入（共 20,880 种）穷举对拍，
  n=6/n=8 随机数千例对拍暴力枚举器（`tests/brute.py`）；
- `test_redundant.py`：单个赘余标记修复——n=3、n=4 全枚举与
  n=5..8 随机样例对拍暴力枚举器（含删除位置枚举），核验最优性、
  锁定位置不可删不可改、同串不同删位时取最小下标、字典序优先于删位，
  以及偶数长度与 `repair` 完全一致；
- `test_specific.py`：全锁定合法/非法、交叉闭合（`([)]`）、同成本多解
  字典序、锁定位置不被改动、NO_REPAIR、n=160 性能；
- `test_api.py`：两个端点的 HTTP 200/NO_REPAIR 响应核验与 422 校验。
