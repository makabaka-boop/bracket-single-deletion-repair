"""请求/响应模型。

校验规则：
- /repair：tokens 为 2..160 个、长度必须为偶数；
- /repair-redundant：tokens 为 3..81 个，奇偶均可（奇数长度期望删去
  恰好一个赘余标记）；
- 每项仅含 char 与 locked 两个字段，额外字段一律 422；
- char 只能是 ()[]{} 之一（Literal 同时保证是字符串）；
- locked 必须是严格的 JSON 布尔值（StrictBool 拒绝 0/1、"true" 等）。
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

BracketChar = Literal["(", ")", "[", "]", "{", "}"]


class TokenIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    char: BracketChar
    locked: StrictBool


class RepairRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tokens: List[TokenIn] = Field(min_length=2, max_length=160)

    @model_validator(mode="after")
    def _even_length(self) -> "RepairRequest":
        if len(self.tokens) % 2 != 0:
            raise ValueError("tokens length must be even")
        return self


class ChangeItem(BaseModel):
    index: int
    before: BracketChar
    after: BracketChar


class RepairResponse(BaseModel):
    status: Literal["OK", "NO_REPAIR"]
    repaired: Optional[str] = None
    pairs: Optional[List[List[int]]] = None
    changes: Optional[List[ChangeItem]] = None


class RedundantRepairRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tokens: List[TokenIn] = Field(min_length=3, max_length=81)


class RedundantRepairResponse(BaseModel):
    status: Literal["OK", "NO_REPAIR"]
    repaired: Optional[str] = None
    pairs: Optional[List[List[int]]] = None
    changes: Optional[List[ChangeItem]] = None
    # 被删除位置的原稿零基下标；未删除（偶数长度）或 NO_REPAIR 时为 null
    deletedIndex: Optional[int] = None
