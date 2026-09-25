# 宏修复 API（Macro Repair）

自动装配机的工艺宏用三种成对括号 `()`、`[]`、`{}` 表示嵌套步骤。本服务对
抄录错误（开始/结束标记颠倒、类型错配等）进行**最小代价修复**：仅允许改动
人工未确认（`locked=false`）的位置。

## 规则

1. 输入为 2..160 个、偶数个 token；每项只有两个字段：
   - `char`：只能是 `(`、`)`、`[`、`]`、`{`、`}` 之一；
   - `locked`：严格布尔值。
   额外字段、类型错误、奇数长度均返回 `422`。
2. 只允许修改 `locked=false` 的位置；锁定内容不会被放宽。
3. 优化目标：先最小化修改数，再按 `(` `)` `[` `]` `{` `}` 的顺序取
   字典序最小的结果（该顺序与 ASCII 码序一致）。
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

## 算法（区间 DP）

`app/repair.py` 中 `dp[i][j]` 记录把区间 `[i, j)` 修复为合法序列的
`(最小修改数, 字典序最小串)`：

- 空区间代价为 0；
- 枚举与位置 `i` 配对的 `k`（步长 2，保证两个子区间均为偶数长度），
  再枚举三种括号对（受 `locked` 约束），合并子区间结果；
- 转移按 `(cost, text)` 取最小；无解状态标记为不可达。

状态数 O(n²)、每状态 O(n) 次转移，总复杂度 O(n³)；n=160 实测约 0.3s。
配对下标由修复结果用栈重建。

## 测试

`tests/` 包含：

- `test_exhaustive.py`：n=2、n=4 对全部输入（共 20,880 种）穷举对拍，
  n=6/n=8 随机数千例对拍暴力枚举器（`tests/brute.py`）；
- `test_specific.py`：全锁定合法/非法、交叉闭合（`([)]`）、同成本多解
  字典序、锁定位置不被改动、NO_REPAIR、n=160 性能；
- `test_api.py`：HTTP 200/NO_REPAIR 响应核验与 14 类 422 校验。
