"""
Business logic layer - separates data access from API routes
"""
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import logging

from app.data_loader import data_manager
from app.models import (
    DashboardStats,
    CostByExperiment,
    DailyCost,
    AccuracyCurve,
    ExperimentFilter,
)

logger = logging.getLogger(__name__)


class ExperimentService:
    """Service for experiment-related operations"""

    @staticmethod
    def get_experiments(
        page: int = 1,
        page_size: int = 20,
        filters: Optional[ExperimentFilter] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Dict], int]:
        """Get paginated experiments"""
        offset = (page - 1) * page_size

        filter_dict = {}
        if filters:
            filter_dict = {
                k: v for k, v in filters.model_dump().items() if v is not None
            }

        experiments, total = data_manager.get_experiments(
            offset=offset,
            limit=page_size,
            filters=filter_dict,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Enrich with computed fields
        for exp in experiments:
            exp["total_trials"] = int(exp.get("trial_count", 0))
            exp["total_cost"] = float(exp.get("costs", 0))
            exp["avg_accuracy"] = exp.get("accuracy")

        return experiments, total

    @staticmethod
    def get_experiment_details(experiment_id: int) -> Optional[Dict]:
        """Get detailed experiment information"""
        exp = data_manager.get_experiment_by_id(experiment_id)
        if not exp:
            return None

        # Add computed fields
        trials = data_manager.get_trials_by_experiment(experiment_id)
        exp["total_trials"] = len(trials)
        exp["finished_trials"] = len(
            [t for t in trials if t["status"] == "finished"])
        exp["failed_trials"] = len(
            [t for t in trials if t["status"] == "failed"])

        return exp

    @staticmethod
    def get_experiment_trials(
        experiment_id: int, status: Optional[str] = None
    ) -> List[Dict]:
        """Get all trials for an experiment"""
        return data_manager.get_trials_by_experiment(experiment_id, status)

    @staticmethod
    def get_accuracy_curve(experiment_id: int) -> List[AccuracyCurve]:
        """Get accuracy curve data for visualization"""
        data = data_manager.get_accuracy_curve(experiment_id)
        return [AccuracyCurve(**d) for d in data]


class TrialService:
    """Service for trial-related operations"""

    @staticmethod
    def get_trial_runs(trial_id: int) -> List[Dict]:
        """Get all runs for a trial"""
        runs = data_manager.get_runs_by_trial(trial_id)

        # Add any computed fields if needed
        for run in runs:
            run["cost_per_token"] = (
                run["costs"] / run["tokens"] if run.get("tokens", 0) > 0 else 0
            )

        return runs

    @staticmethod
    def get_trial_stats(trial_id: int) -> Dict:
        """Get aggregated stats for a trial"""
        runs = data_manager.get_runs_by_trial(trial_id)

        if not runs:
            return {
                "total_runs": 0,
                "total_cost": 0,
                "avg_latency": 0,
                "total_tokens": 0,
            }

        return {
            "total_runs": len(runs),
            "total_cost": sum(r["costs"] for r in runs),
            "avg_latency": sum(r["latency_ms"] for r in runs) / len(runs),
            "total_tokens": sum(r["tokens"] for r in runs),
            "min_latency": min(r["latency_ms"] for r in runs),
            "max_latency": max(r["latency_ms"] for r in runs),
        }

    @staticmethod
    def get_trial_details(trial_id: int):
        """Get detailed trial information"""
        # Find the trial in the dataframe
        trial_row = data_manager.trials_df[data_manager.trials_df['id'] == trial_id]
        if trial_row.empty:
            return None

        trial = trial_row.iloc[0].to_dict()

        # Get the experiment name
        exp_row = data_manager.experiments_df[data_manager.experiments_df['id']
                                              == trial['experiment_id']]
        if not exp_row.empty:
            trial['experiment_name'] = exp_row.iloc[0]['experiment_name']

        # Add run statistics
        runs = data_manager.get_runs_by_trial(trial_id)
        if runs:
            trial['total_runs'] = len(runs)
            trial['total_cost'] = sum(r['costs'] for r in runs)
            trial['avg_latency'] = sum(r['latency_ms']
                                       for r in runs) / len(runs)
            trial['total_tokens'] = sum(r['tokens'] for r in runs)

        return trial


class MetricsService:
    """Service for metrics and analytics"""

    @staticmethod
    @lru_cache(maxsize=1, typed=False)
    def get_dashboard_stats() -> DashboardStats:
        """Get cached dashboard statistics"""
        stats = data_manager.get_dashboard_stats()
        return DashboardStats(**stats)

    @staticmethod
    @lru_cache(maxsize=1)
    def get_cost_breakdown() -> List[CostByExperiment]:
        """Get cost breakdown by experiment"""
        data = data_manager.get_cost_by_experiment()
        return [CostByExperiment(**item) for item in data]

    @staticmethod
    def get_daily_costs(days: int = 30) -> List[DailyCost]:
        """Get daily cost trends"""
        data = data_manager.get_daily_costs(days)
        return [DailyCost(**item) for item in data]

    @staticmethod
    def get_performance_metrics() -> Dict:
        """Get various performance metrics"""
        return {
            "avg_tokens_per_run": float(data_manager.runs_df["tokens"].mean()),
            "median_latency": float(data_manager.runs_df["latency_ms"].median()),
            "p95_latency": float(data_manager.runs_df["latency_ms"].quantile(0.95)),
            "cost_per_token": float(
                data_manager.runs_df["costs"].sum()
                / data_manager.runs_df["tokens"].sum()
            ),
            "hourly_run_rate": len(data_manager.runs_df) / 24,  # Simplified
        }

    @staticmethod
    def clear_cache():
        """Clear all cached metrics"""
        MetricsService.get_dashboard_stats.cache_clear()
        MetricsService.get_cost_breakdown.cache_clear()
        logger.info("Metrics cache cleared")


class SearchService:
    """Service for search functionality"""

    @staticmethod
    def search(query: str, limit: int = 20) -> Dict[str, Any]:
        """Perform full-text search across all entities"""
        if not query or len(query) < 2:
            return {"experiments": [], "trials": [], "runs": []}

        results = data_manager.search(query)

        # Limit results
        for key in results:
            results[key] = results[key][:limit]

        return results

    @staticmethod
    def get_suggestions(prefix: str) -> List[str]:
        """Get autocomplete suggestions"""
        if not prefix or len(prefix) < 2:
            return []

        prefix_lower = prefix.lower()
        suggestions = set()

        # Get experiment names
        for name in data_manager.experiments_df["name"]:
            if name.lower().startswith(prefix_lower):
                suggestions.add(name)

        # Get project IDs
        for project in data_manager.experiments_df["project_id"].unique():
            if project.lower().startswith(prefix_lower):
                suggestions.add(project)

        return sorted(list(suggestions))[:10]


class AnalyticsService:
    """Advanced analytics service"""

    @staticmethod
    def detect_anomalies() -> List[Dict]:
        """Detect cost or performance anomalies"""
        anomalies = []

        # Detect high-cost runs
        cost_threshold = data_manager.runs_df["costs"].quantile(0.95)
        high_cost_runs = data_manager.runs_df[
            data_manager.runs_df["costs"] > cost_threshold
        ]

        for _, run in high_cost_runs.iterrows():
            anomalies.append(
                {
                    "type": "high_cost",
                    "trial_id": int(run["trial_id"]),
                    "value": float(run["costs"]),
                    "threshold": float(cost_threshold),
                    "severity": "warning",
                }
            )

        # Detect failed trials pattern
        failed_by_exp = (
            data_manager.trials_df[data_manager.trials_df["status"] == "failed"]
            .groupby("experiment_id")
            .size()
        )

        for exp_id, count in failed_by_exp.items():
            if count > 2:  # More than 2 failures
                anomalies.append(
                    {
                        "type": "high_failure_rate",
                        "experiment_id": int(exp_id),
                        "failed_count": int(count),
                        "severity": "critical",
                    }
                )

        return anomalies

    @staticmethod
    def get_trends() -> Dict:
        """Calculate trends and insights"""
        # Calculate accuracy trend
        finished_trials = data_manager.trials_df[
            data_manager.trials_df["status"] == "finished"
        ].sort_values("created_at")

        # Rolling mean for accuracy
        if len(finished_trials) > 5:
            accuracy_trend = finished_trials["accuracy"].rolling(
                window=5).mean()
            improving = (
                accuracy_trend.iloc[-1] > accuracy_trend.iloc[-5]
                if len(accuracy_trend) >= 5
                else None
            )
        else:
            improving = None

        # Cost trend
        daily_costs = data_manager.get_daily_costs(7)
        if len(daily_costs) >= 2:
            cost_trend = (
                "increasing"
                if daily_costs[-1]["total_cost"] > daily_costs[0]["total_cost"]
                else "decreasing"
            )
        else:
            cost_trend = "stable"

        return {
            "accuracy_improving": improving,
            "cost_trend": cost_trend,
            "avg_trial_duration": float(
                data_manager.trials_df["duration_seconds"].mean()
            )
            if "duration_seconds" in data_manager.trials_df.columns
            else None,
            # experiments per day
            "experiment_velocity": len(data_manager.experiments_df) / 30,
        }
