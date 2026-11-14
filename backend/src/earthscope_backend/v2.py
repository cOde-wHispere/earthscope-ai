"""Discovery and descriptive endpoints; no new trend/inference routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from earthscope_backend.dataset_registry import RegistryEntry
from earthscope_backend.multivariable_schemas import (
    DatasetCatalog,
    DescriptiveAnnualResponse,
    DescriptiveMonthlyResponse,
    VariableMetadata,
)
from earthscope_backend.schemas import ErrorResponse

router = APIRouter(prefix="/v2/datasets", tags=["Verified descriptive datasets"])
ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Dataset ID is not approved"},
    503: {"model": ErrorResponse, "description": "This dataset is unavailable or invalid"},
}


def require_entry(request: Request, dataset_id: str) -> RegistryEntry | JSONResponse:
    entry = request.app.state.dataset_registry.entries.get(dataset_id)
    if entry is None:
        error = ErrorResponse(code="dataset_not_found", message="Dataset ID is not approved.")
        return JSONResponse(status_code=404, content=error.model_dump(mode="json"))
    if entry.catalog.error is not None:
        return JSONResponse(status_code=503, content=entry.catalog.error.model_dump(mode="json"))
    return entry


@router.get("", response_model=DatasetCatalog)
def datasets(request: Request):
    return request.app.state.dataset_registry.catalog


@router.get("/{dataset_id}/metadata", response_model=VariableMetadata, responses=ERROR_RESPONSES)
def metadata(request: Request, dataset_id: str):
    entry = require_entry(request, dataset_id)
    return entry if isinstance(entry, JSONResponse) else entry.metadata


@router.get(
    "/{dataset_id}/timeseries/monthly",
    response_model=DescriptiveMonthlyResponse,
    responses=ERROR_RESPONSES,
)
def monthly(request: Request, dataset_id: str):
    entry = require_entry(request, dataset_id)
    return entry if isinstance(entry, JSONResponse) else entry.monthly


@router.get(
    "/{dataset_id}/timeseries/annual",
    response_model=DescriptiveAnnualResponse,
    responses=ERROR_RESPONSES,
)
def annual(request: Request, dataset_id: str):
    entry = require_entry(request, dataset_id)
    return entry if isinstance(entry, JSONResponse) else entry.annual
