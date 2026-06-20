from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.analysis import (
    DecomposeIndustryRequest,
    DecomposeIndustryResponse,
    IndustryNode,
    UpdateIndustryNodeRequest,
    UpsertIndustryNodeRequest,
)
from app.services.industry_service import IndustryService


router = APIRouter(prefix="/api/industry", tags=["industry"])


@router.post("/decompose", response_model=DecomposeIndustryResponse)
def decompose(payload: DecomposeIndustryRequest) -> DecomposeIndustryResponse:
    nodes, warnings, source = IndustryService().decompose(
        keyword=payload.keyword,
        analysis_id=payload.analysis_id,
        api_config=payload.api_config,
    )
    return DecomposeIndustryResponse(
        keyword=payload.keyword,
        nodes=nodes,
        source=source,
        warnings=warnings,
    )


@router.post("/nodes", response_model=IndustryNode)
def create_node(payload: UpsertIndustryNodeRequest) -> IndustryNode:
    return IndustryService().create_node(payload)


@router.patch("/nodes/{node_id}", response_model=IndustryNode)
def update_node(node_id: str, payload: UpdateIndustryNodeRequest) -> IndustryNode:
    node = IndustryService().update_node(node_id, payload)
    if node is None:
        raise HTTPException(status_code=404, detail="industry node not found")
    return node


@router.delete("/nodes/{node_id}")
def delete_node(node_id: str) -> dict[str, bool]:
    deleted = IndustryService().delete_node(node_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="industry node not found")
    return {"deleted": True}
