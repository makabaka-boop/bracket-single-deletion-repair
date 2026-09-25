"""FastAPI 入口：POST /repair 修复括号宏；POST /repair-redundant 单个赘余标记修复。"""

from __future__ import annotations

from fastapi import FastAPI

from .repair import repair, repair_redundant
from .schemas import (
    ChangeItem,
    RedundantRepairRequest,
    RedundantRepairResponse,
    RepairRequest,
    RepairResponse,
)

app = FastAPI(title="Macro Repair API", version="1.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/repair", response_model=RepairResponse)
def repair_endpoint(req: RepairRequest) -> RepairResponse:
    chars = [t.char for t in req.tokens]
    locked = [t.locked for t in req.tokens]

    outcome = repair(chars, locked)
    if outcome is None:
        return RepairResponse(status="NO_REPAIR")

    result, pairs = outcome
    changes = [
        ChangeItem(index=i, before=before, after=after)
        for i, (before, after) in enumerate(zip(chars, result))
        if before != after
    ]
    return RepairResponse(
        status="OK",
        repaired=result,
        pairs=pairs,
        changes=changes,
    )


@app.post("/repair-redundant", response_model=RedundantRepairResponse)
def repair_redundant_endpoint(req: RedundantRepairRequest) -> RedundantRepairResponse:
    chars = [t.char for t in req.tokens]
    locked = [t.locked for t in req.tokens]

    outcome = repair_redundant(chars, locked)
    if outcome is None:
        return RedundantRepairResponse(status="NO_REPAIR")

    result, pairs, deleted = outcome
    # 改动清单回指原稿坐标：被删位置不列入 changes，单独以 deletedIndex 给出
    changes = []
    for i, before in enumerate(chars):
        if i == deleted:
            continue
        p = i if deleted is None or i < deleted else i - 1
        after = result[p]
        if before != after:
            changes.append(ChangeItem(index=i, before=before, after=after))
    return RedundantRepairResponse(
        status="OK",
        repaired=result,
        pairs=pairs,
        changes=changes,
        deletedIndex=deleted,
    )
