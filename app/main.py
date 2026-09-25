"""FastAPI 入口：括号宏修复 API。"""

from __future__ import annotations

from fastapi import FastAPI

from .repair import repair, repair_single_deletion
from .schemas import (
    ChangeItem,
    RepairRequest,
    RepairResponse,
    SingleDeletionRepairRequest,
    SingleDeletionRepairResponse,
)

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


@app.post(
    "/repair-single-deletion",
    response_model=SingleDeletionRepairResponse,
)
def repair_single_deletion_endpoint(
    req: SingleDeletionRepairRequest,
) -> SingleDeletionRepairResponse:
    chars = [t.char for t in req.tokens]
    locked = [t.locked for t in req.tokens]

    outcome = repair_single_deletion(chars, locked)
    if outcome is None:
        return SingleDeletionRepairResponse(status="NO_REPAIR")

    changes = [
        ChangeItem(index=index, before=before, after=after)
        for index, before, after in outcome.changes
    ]
    return SingleDeletionRepairResponse(
        status="OK",
        repaired=outcome.text,
        pairs=outcome.pairs,
        changes=changes,
        deleted_index=outcome.deleted_index,
    )
