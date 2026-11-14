"""Read-only API over one validated snapshot loaded at application startup."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from earthscope_backend import config
from earthscope_backend.analysis import (
    AnalysisError,
    annual_series,
    climatology,
    estimate_trend,
    monthly_series,
)
from earthscope_backend.identity import (
    DatasetIdentity,
    load_baseline_identity,
    load_verified_dataset,
)
from earthscope_backend.importer import (
    Dataset,
    DatasetUnavailableError,
    DatasetValidationError,
)
from earthscope_backend.schemas import (
    AnnualResponse,
    ClimatologyResponse,
    DatasetMetadata,
    ErrorResponse,
    HealthResponse,
    MonthlyResponse,
    TrendResponse,
)


class ServiceError(Exception):
    def __init__(self, error: ErrorResponse):
        self.error = error


def create_app(path: Path | None = None, *, identity: DatasetIdentity | None = None) -> FastAPI:
    source_path = path if path is not None else config.data_path()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.dataset = None
        app.state.error = None
        app.state.trend = None
        app.state.trend_error = None
        app.state.dataset_status = "unavailable"
        try:
            approved_identity = identity if identity is not None else load_baseline_identity()
            dataset = load_verified_dataset(source_path, approved_identity)
            app.state.dataset = dataset
            app.state.monthly = monthly_series(dataset)
            app.state.annual = annual_series(dataset)
            app.state.climatology = climatology(dataset)
            app.state.dataset_status = "ready"
            try:
                app.state.trend = estimate_trend(dataset)
            except AnalysisError as exc:
                app.state.dataset_status = "analysis_unavailable"
                app.state.trend_error = ErrorResponse(code="analysis_unavailable", message=str(exc))
        except DatasetUnavailableError as exc:
            app.state.dataset_status = "missing" if exc.code == "dataset_missing" else "unavailable"
            app.state.error = ErrorResponse(code=exc.code, message=str(exc))
        except DatasetValidationError as exc:
            app.state.dataset_status = "invalid"
            app.state.error = ErrorResponse(
                code="dataset_invalid",
                message="Source validation failed. Correct the listed source issues and restart.",
                validation=exc.summary,
            )
        yield

    app = FastAPI(title="EarthScope AI Scientific Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins(),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept"],
    )

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError):
        return JSONResponse(status_code=503, content=exc.error.model_dump(mode="json"))

    def require_dataset(request: Request) -> Dataset:
        if request.app.state.error is not None:
            raise ServiceError(request.app.state.error)
        return request.app.state.dataset

    dataset_dependency = Annotated[Dataset, Depends(require_dataset)]
    unavailable_response = {
        503: {"model": ErrorResponse, "description": "Source or analysis unavailable"}
    }

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request):
        error = request.app.state.error or request.app.state.trend_error
        return HealthResponse(
            status="degraded" if error else "ok",
            dataset_status=request.app.state.dataset_status,
            error=error,
        )

    @app.get("/metadata", response_model=DatasetMetadata, responses=unavailable_response)
    def metadata(dataset: dataset_dependency):
        return dataset.metadata

    @app.get("/timeseries/monthly", response_model=MonthlyResponse, responses=unavailable_response)
    def monthly(request: Request, dataset: dataset_dependency):
        return request.app.state.monthly

    @app.get("/timeseries/annual", response_model=AnnualResponse, responses=unavailable_response)
    def annual(request: Request, dataset: dataset_dependency):
        return request.app.state.annual

    @app.get("/climatology", response_model=ClimatologyResponse, responses=unavailable_response)
    def baseline(request: Request, dataset: dataset_dependency):
        return request.app.state.climatology

    @app.get("/trend", response_model=TrendResponse, responses=unavailable_response)
    def trend(request: Request, dataset: dataset_dependency):
        if request.app.state.trend_error is not None:
            raise ServiceError(request.app.state.trend_error)
        return request.app.state.trend

    return app


app = create_app()
