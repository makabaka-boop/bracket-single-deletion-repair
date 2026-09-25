# 宏修复 API（Macro Repair）

自动装配机的工艺宏用三种成对括号 `()`、`[]`、`{}` 表示嵌套步骤。本服务对
抄录错误（开始/结束标记颠倒、类型错配、偶发赘余标记等）进行**最小代价修复**：
仅允许改动人工未确认（`locked=false`）的位置。

## 规则

### `POST /repair`

1. 输入为 2..160 个、偶数个 token；每项只有两个字段：
   - `char`：只能是 `(`、`)`、`[`、`]`、`{`、`}` 之一；
   - `locked`：严格布尔值。
   额外字段、类型错误、奇数长度均返回 `422`。
2. 只允许修改 `locked=false` 的位置；锁定内容不会被放宽。
3. 优化目标：先最小化修改数，再按 `(` `)` `[` `]` `{` `}` 的顺序取
   字典序最小的结果（该顺序与 ASCII 码序一致）。
4. 不存在可行方案时返回 `NO_REPAIR`。

### `POST /repair-single-deletion`

用于修复“多抄了一个未确认标记”的独立入口：

1. 输入为 3..81 个 token，奇数、偶数长度均可；token 字段与类型校验与
   `/repair` 相同。
2. 至多删除一个 `locked=false` 的原稿位置；其余未锁定位置只可按原规则替换。
   删除与每次替换各计一次修改，锁定位置既不能删除也不能替换。
3. 奇数长度必须恰好删除一个位置；偶数长度删除后会成为奇数，不可能合法，
   因此偶数长度等价于不删除，结果与 `/repair` 完全一致。
4. 优化目标依次为：
   1. 总修改数最少；
   2. 修复串按 `(` `)` `[` `]` `{` `}` 的顺序字典序最小；
   3. 修复串仍并列时，删除的原稿零基下标最小。
5. 奇数长度下如果没有未锁定可删位，或锁定约束导致删除后仍无法配对，返回
   `NO_REPAIR`；不会返回只配对一部分的结果。

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

`POST /repair-single-deletion`

```json
{
  "tokens": [
    {"char": "(", "locked": false},
    {"char": ")", "locked": false},
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

- `pairs`：配对下标 `[open_index, close_index]`，按开括号下标升序，
  0 基，覆盖全部保留位置，可逐位置核验。
- `changes`：替换项的原稿下标及改动前后字符；锁定位置不会出现。删除项不混入
  `changes`，而是单独放在 `deletedIndex`。
- `deletedIndex`：被删除位置的原稿零基下标；偶数长度不删除时为 `null`。

无解：

```json
{"status": "NO_REPAIR", "repaired": null, "pairs": null, "changes": null, "deletedIndex": null}
```

## 算法（区间 DP）

`app/repair.py` 中普通修复器的 `dp[i][j]` 记录把区间 `[i, j)` 修复为合法序列的
`(最小修改数, 字典序最小串)`：

- 空区间代价为 0；
- 枚举与位置 `i` 配对的 `k`（步长 2，保证两个子区间均为偶数长度），
  再枚举三种括号对（受 `locked` 约束），合并子区间结果；
- 转移按 `(cost, text)` 取最小；无解状态标记为不可达。

单个赘余标记修复器使用 `dp[used][i][j]`：

- `used=0/1` 表示该区间是否已经使用删除；
- 状态同时保存修复串、每个修复字符对应的原稿坐标和 `deletedIndex`，
  因此不会因为先压缩字符串而丢失原始下标；
- 保留 `i` 作为开括号时，删除权只能落在 `[i+1,k)` 或 `[k+1,j)` 之一；
  也可以直接删除未锁定的 `i`，再与剩余区间组合；
- 转移按 `(总修改数, 修复串, 删除下标)` 取最小。

普通修复器状态数 O(n²)、每状态 O(n) 次转移，总复杂度 O(n³)；n=160 实测约 0.3s。
单个赘余标记修复器状态数为常数倍 O(n²)，复杂度同样为 O(n³)；n=81 毫秒级完成。
配对下标由修复结果和保存的原稿坐标用栈重建。

## 测试

`tests/` 包含：

- `test_exhaustive.py`：普通修复器 n=2、n=4 全部输入（共 20,880 种）穷举对拍，
  n=6/n=8 随机数千例对拍暴力枚举器（`tests/brute.py`）；
- `test_specific.py`：全锁定合法/非法、交叉闭合（`([)]`）、同成本多解
  字典序、锁定位置不被改动、NO_REPAIR、n=160 性能；
- `test_single_deletion.py`：新修复器 n=3/n=4 穷举删除和替换、锁定保护、
  偶数长度与原修复器一致、同修复串不同删位的下标裁决；n=5..8 随机对拍；
- `test_api.py`、`test_single_deletion_api.py`：HTTP 200/NO_REPAIR 响应核验、
  原稿坐标与 422 校验；原 `/repair` 的奇数长度 422 保持不变。
