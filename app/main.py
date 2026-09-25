"""FastAPI 入口：POST /repair 修复括号宏。"""

from __future__ import annotations

from fastapi import FastAPI

from .repair import repair
from .schemas import ChangeItem, RepairRequest, RepairResponse

app = FastAPI(title="Macro Repair API", version="1.0.0")


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
