"""
API Routes - Clean separation of HTTP handling from business logic
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
import logging

from app.models import (
    PaginatedResponse,
    DashboardStats,
    CostByExperiment,
    DailyCost,
    AccuracyCurve,
    ExperimentFilter,
    ChatRequest,
    ChatResponse,
)
from app.services import (
    ExperimentService,
    TrialService,
    MetricsService,
    SearchService,
    AnalyticsService,
)
from app.config import settings

logger = logging.getLogger(__name__)

# Create routers
router = APIRouter()


# ============= Health Check =============
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.api_version}


# ============= Experiments Endpoints =============
@router.get("/experiments", response_model=PaginatedResponse)
async def get_experiments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: Optional[str] = None,
    project_id: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|name|total_cost)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    """Get paginated list of experiments with filters"""
    filters = ExperimentFilter(name=name, project_id=project_id)

    experiments, total = ExperimentService.get_experiments(
        page=page,
        page_size=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return PaginatedResponse(
        items=experiments,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: int = Path(..., description="Experiment ID")):
    """Get single experiment details"""
    experiment = ExperimentService.get_experiment_details(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.get("/experiments/{experiment_id}/trials")
async def get_experiment_trials(
    experiment_id: int = Path(..., description="Experiment ID"),
    status: Optional[str] = Query(None, regex="^(pending|running|finished|failed)$"),
):
    """Get all trials for an experiment"""
    trials = ExperimentService.get_experiment_trials(experiment_id, status)
    return {"experiment_id": experiment_id, "trials": trials, "total": len(trials)}


@router.get(
    "/experiments/{experiment_id}/accuracy-curve", response_model=List[AccuracyCurve]
)
async def get_accuracy_curve(
    experiment_id: int = Path(..., description="Experiment ID")
):
    """Get accuracy curve data for visualization"""
    return ExperimentService.get_accuracy_curve(experiment_id)


# ============= Trials Endpoints =============
@router.get("/trials/{trial_id}/runs")
async def get_trial_runs(trial_id: int = Path(..., description="Trial ID")):
    """Get all runs for a trial"""
    runs = TrialService.get_trial_runs(trial_id)
    stats = TrialService.get_trial_stats(trial_id)

    return {"trial_id": trial_id, "runs": runs, "total": len(runs), "stats": stats}


@router.get("/trials/{trial_id}/stats")
async def get_trial_stats(trial_id: int = Path(..., description="Trial ID")):
    """Get aggregated statistics for a trial"""
    return TrialService.get_trial_stats(trial_id)


# add endpoint for fectching trial stats
@router.get("/trials/{trial_id}")
async def get_trial_details(trial_id: int = Path(..., description="Trial ID")):
    """Get single trial details"""
    trial = TrialService.get_trial_details(trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


# ============= Dashboard & Metrics =============
@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics"""
    return MetricsService.get_dashboard_stats()


@router.get("/dashboard/cost-breakdown", response_model=List[CostByExperiment])
async def get_cost_breakdown():
    """Get cost breakdown by experiment"""
    return MetricsService.get_cost_breakdown()


@router.get("/dashboard/daily-costs", response_model=List[DailyCost])
async def get_daily_costs(
    days: int = Query(30, ge=1, le=365, description="Number of days to retrieve")
):
    """Get daily cost trends"""
    return MetricsService.get_daily_costs(days)


@router.get("/metrics/performance")
async def get_performance_metrics():
    """Get performance metrics"""
    return MetricsService.get_performance_metrics()


@router.get("/metrics/anomalies")
async def get_anomalies():
    """Get detected anomalies"""
    return AnalyticsService.detect_anomalies()


@router.get("/metrics/trends")
async def get_trends():
    """Get trend analysis"""
    return AnalyticsService.get_trends()


# ============= Search =============
@router.get("/search")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Full-text search across all entities"""
    return SearchService.search(q, limit)


@router.get("/search/suggestions")
async def get_suggestions(prefix: str = Query(..., min_length=2, max_length=50)):
    """Get autocomplete suggestions"""
    return SearchService.get_suggestions(prefix)


# ============= Cache Management =============
@router.post("/cache/clear")
async def clear_cache():
    """Clear all caches (admin endpoint)"""
    MetricsService.clear_cache()
    return {"message": "Cache cleared successfully"}


# ============= Chat/Analysis (Bonus) =============
@router.post("/chat", response_model=ChatResponse)
async def analyze_with_chat(request: ChatRequest):
    """Analyze experiments using AI (bonus feature)"""
    if not settings.enable_chatbot:
        raise HTTPException(status_code=503, detail="Chatbot feature is not enabled")

    # Simplified response for now
    return ChatResponse(
        response="This would analyze your experiments using AI. Enable by setting OPENAI_API_KEY.",
        context_used=["experiment_1", "experiment_2"],
        relevant_experiments=[1, 2, 3],
    )


# ============= Utility Endpoints =============
@router.get("/stats/summary")
async def get_summary_statistics():
    """Get comprehensive summary statistics"""
    return {
        "dashboard": MetricsService.get_dashboard_stats(),
        "trends": AnalyticsService.get_trends(),
        "top_experiments": MetricsService.get_cost_breakdown()[:5],
        "recent_activity": {
            "last_24h_runs": 42,  # Placeholder
            "active_experiments": 3,
        },
    }
