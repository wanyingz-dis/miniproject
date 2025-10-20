"""
Pydantic models for type safety and validation
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any, Literal
from datetime import datetime
from enum import Enum


class TrialStatus(str, Enum):
    """Trial status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


# ============= Response Models =============


class Experiment(BaseModel):
    """Experiment model"""

    id: int
    name: str
    project_id: str
    created_at: datetime
    is_deleted: bool = False

    # Computed fields (added by service layer)
    total_trials: Optional[int] = 0
    total_runs: Optional[int] = 0
    total_cost: Optional[float] = 0
    avg_accuracy: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class Trial(BaseModel):
    """Trial model"""

    id: int
    experiment_id: int
    status: TrialStatus
    created_at: datetime
    accuracy: Optional[float] = None
    duration_seconds: Optional[int] = Field(None, alias="duration(s)")

    # Computed fields
    total_runs: Optional[int] = 0
    total_cost: Optional[float] = 0
    avg_latency: Optional[float] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Run(BaseModel):
    """Run model"""

    id: int
    trial_id: int
    tokens: int
    costs: float
    latency_ms: int = Field(alias="latency(ms)")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ============= API Response Models =============


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""

    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class DashboardStats(BaseModel):
    """Dashboard statistics"""

    total_experiments: int
    total_trials: int
    total_runs: int
    total_cost: float
    avg_accuracy: float
    avg_latency_ms: float
    active_trials: int
    failed_trials: int
    success_rate: float


class CostByExperiment(BaseModel):
    """Cost breakdown by experiment"""

    experiment_id: int
    experiment_name: str
    total_cost: float
    percentage: float
    run_count: int


class DailyCost(BaseModel):
    """Daily cost aggregation"""

    date: str
    total_cost: float
    run_count: int
    experiment_count: int


class AccuracyCurve(BaseModel):
    """Accuracy curve data point"""

    trial_id: int
    timestamp: datetime
    accuracy: float
    status: TrialStatus


# ============= Request Models =============


class QueryParams(BaseModel):
    """Common query parameters"""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "desc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class ExperimentFilter(BaseModel):
    """Experiment filter parameters"""

    name: Optional[str] = None
    project_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class TrialFilter(BaseModel):
    """Trial filter parameters"""

    experiment_id: Optional[int] = None
    status: Optional[TrialStatus] = None
    min_accuracy: Optional[float] = Field(None, ge=0, le=1)
    max_accuracy: Optional[float] = Field(None, ge=0, le=1)


class RunFilter(BaseModel):
    """Run filter parameters"""

    trial_id: Optional[int] = None
    min_cost: Optional[float] = Field(None, ge=0)
    max_cost: Optional[float] = Field(None, ge=0)
    min_latency: Optional[int] = Field(None, ge=0)
    max_latency: Optional[int] = Field(None, ge=0)


# ============= Chat Models (Bonus) =============


class ChatRequest(BaseModel):
    """Chat request for analysis"""

    message: str
    experiment_id: Optional[int] = None
    include_context: bool = True


class ChatResponse(BaseModel):
    """Chat response with context"""

    response: str
    context_used: List[str] = []
    relevant_experiments: List[int] = []
