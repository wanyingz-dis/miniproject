"""
CSV Data Loader with in-memory caching and safe, explicit joins.

Why this version?
- Never leaves 'id' as an index (prevents the classic pandas merge ambiguity).
- Normalizes columns (renames CSV quirks like 'duration(s)' → 'duration_seconds').
- Parses datetimes robustly (different formats across files).
- Uses explicit merge keys (left_on / right_on) so pandas never "guesses".
- Small, readable helpers + human comments so future-you understands it fast.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional, Dict, List, Any, Tuple

import numpy as np
import pandas as pd

from app.config import settings
from app.models import TrialStatus  # Enum (pending/running/finished/failed)

logger = logging.getLogger(__name__)


# ---- small helpers (pure functions) ---------------------------------------

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Make a DataFrame safe to join:
    - reset any index back to columns (so 'id' can't be both index & column)
    - drop duplicated column names (can happen after weird CSV exports)
    - return a copy to avoid chained-assignment surprises
    """
    out = df.copy()
    if out.index.name is not None or getattr(out.index, "names", [None]) != [None]:
        out = out.reset_index()
    out = out.loc[:, ~out.columns.duplicated()]
    return out


def _parse_dt(series: pd.Series, *, fmt: str | None = None, dayfirst: bool | None = None) -> pd.Series:
    """Parse datetimes tolerant to format differences across files."""
    # If a strict format is provided, try that first; fall back to best-effort.
    if fmt:
        s = pd.to_datetime(series, format=fmt, errors="coerce")
        # If many NaT, try a best-effort parse as a fallback
        if s.isna().mean() > 0.5:
            s = pd.to_datetime(series, errors="coerce",
                               dayfirst=bool(dayfirst))
        return s
    return pd.to_datetime(series, errors="coerce", dayfirst=bool(dayfirst))


def _safe_lower(series: pd.Series) -> pd.Series:
    """Lowercase strings safely (keeps NaN as-is)."""
    return series.astype("string").str.lower()


# ---- DataManager -----------------------------------------------------------

class DataManager:
    """
    Manages CSV data loading and provides efficient querying interface.
    The goal is correctness + clarity over cleverness.
    """

    def __init__(self):
        self.experiments_df: Optional[pd.DataFrame] = None
        self.trials_df: Optional[pd.DataFrame] = None
        self.runs_df: Optional[pd.DataFrame] = None
        self._initialized = False

    def initialize(self) -> None:
        """Load all CSV files into memory on startup."""
        try:
            logger.info("Loading CSV data into memory...")

            # -- Experiments ---------------------------------------------------
            exp = pd.read_csv(settings.experiments_path)
            # Created-at in experiments often ISO-like; be tolerant.
            exp["created_at"] = _parse_dt(exp["created_at"])

            # add rename_map for exp naming consistency
            rename_map = {
                "experiment name": "name",
                "Experiment Name": "name",
                "is_del": "is_deleted",
            }
            exp = exp.rename(
                columns={k: v for k, v in rename_map.items() if k in exp.columns})
            if "is_deleted" in exp.columns:
                exp["is_deleted"] = exp["is_deleted"].fillna(
                    False).astype(bool)

            exp = _normalize_df(exp)

            # -- Trials --------------------------------------------------------
            tri = pd.read_csv(settings.trials_path)
            # Provided sample used "DD/MM/YYYY HH:MM" — allow both styles
            tri["created_at"] = _parse_dt(tri["created_at"], dayfirst=True)
            # Normalize quirky CSV header to model field name
            if "duration(s)" in tri.columns and "duration_seconds" not in tri.columns:
                tri = tri.rename(columns={"duration(s)": "duration_seconds"})
            # Keep status as lower-case strings (aligns with TrialStatus values)
            if "status" in tri.columns:
                tri["status"] = _safe_lower(tri["status"])
            tri = _normalize_df(tri)

            # -- Runs ----------------------------------------------------------
            run = pd.read_csv(settings.runs_path)
            run["created_at"] = _parse_dt(run["created_at"], dayfirst=True)
            if "latency(ms)" in run.columns and "latency_ms" not in run.columns:
                run = run.rename(columns={"latency(ms)": "latency_ms"})
            run = _normalize_df(run)

            # Save raw, normalized tables
            self.experiments_df = exp
            self.trials_df = tri
            self.runs_df = run

            # Precompute rollups that the UI needs a lot
            self._precompute_aggregations()

            self._initialized = True
            # Invalidate any cached summaries (e.g., dashboard stats)
            try:
                # type: ignore[attr-defined]
                self.get_dashboard_stats.cache_clear()
            except Exception:
                pass

            logger.info(
                "Data loaded: %d experiments, %d trials, %d runs",
                len(self.experiments_df), len(
                    self.trials_df), len(self.runs_df)
            )

        except Exception as e:
            logger.error("Failed to load CSV data: %s", e)
            raise

    # ---- aggregations ------------------------------------------------------

    def _precompute_aggregations(self) -> None:
        """Compute lightweight aggregates so routes can be snappy."""
        if self.runs_df is not None and self.trials_df is not None:
            # Aggregate runs at the trial level
            runs_agg = (
                self.runs_df.groupby("trial_id", as_index=False)
                .agg(
                    total_cost=("costs", "sum"),
                    total_tokens=("tokens", "sum"),
                    avg_latency_ms=("latency_ms", "mean"),
                    run_count=("id", "count"),
                )
            )
            # Explicit keys: trials.id ↔ runs_agg.trial_id
            self.trials_df = self.trials_df.merge(
                runs_agg, left_on="id", right_on="trial_id", how="left"
            ).drop(columns=["trial_id"], errors="ignore")

            # Fill NA after the merge (trials with zero runs)
            self.trials_df[["total_cost", "total_tokens", "avg_latency_ms", "run_count"]] = (
                self.trials_df[["total_cost", "total_tokens", "avg_latency_ms", "run_count"]].fillna(
                    {"total_cost": 0.0, "total_tokens": 0, "run_count": 0}
                )
            )

        if self.trials_df is not None and self.experiments_df is not None:
            # Aggregate trials at the experiment level
            exp_agg_from_trials = (
                self.trials_df.groupby("experiment_id", as_index=False)
                .agg(
                    avg_accuracy=("accuracy", "mean"),
                    total_cost=("total_cost", "sum"),
                    total_trials=("id", "count"),
                    total_runs=("run_count", "sum"),
                )
            )
            self.experiments_df = self.experiments_df.merge(
                exp_agg_from_trials, left_on="id", right_on="experiment_id", how="left"
            ).drop(columns=["experiment_id"], errors="ignore")

            self.experiments_df[["avg_accuracy", "total_cost", "total_trials", "total_runs"]] = (
                self.experiments_df[["avg_accuracy",
                                     "total_cost", "total_trials", "total_runs"]]
                .fillna({"avg_accuracy": np.nan, "total_cost": 0.0, "total_trials": 0, "total_runs": 0})
            )

    # ---- queries -----------------------------------------------------------

    def get_experiments(
        self,
        offset: int = 0,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Dict], int]:
        """List experiments with simple filters + pagination."""
        df = self.experiments_df.copy()

        # Filters
        if filters:
            if filters.get("name"):
                df = df[df["name"].str.contains(
                    filters["name"], case=False, na=False)]
            if filters.get("project_id"):
                df = df[df["project_id"] == filters["project_id"]]
            if filters.get("created_after") is not None:
                df = df[df["created_at"] >= filters["created_after"]]
            if filters.get("created_before") is not None:
                df = df[df["created_at"] <= filters["created_before"]]

        # Sort
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=(sort_order == "asc"))

        # Page
        total = len(df)
        df = df.iloc[offset: offset + limit]
        return df.to_dict("records"), total

    def get_experiment_by_id(self, experiment_id: int) -> Optional[Dict]:
        """Fetch a single experiment by ID."""
        df = self.experiments_df
        row = df.loc[df["id"] == experiment_id]
        if not row.empty:
            return row.iloc[0].to_dict()
        return None

    def get_trials_by_experiment(
        self, experiment_id: int, status_filter: Optional[str] = None
    ) -> List[Dict]:
        """All trials for an experiment (optionally filter by status)."""
        df = self.trials_df[self.trials_df["experiment_id"] == experiment_id]
        if status_filter:
            df = df[df["status"] == status_filter.lower()]
        df = df.sort_values("created_at")
        return df.to_dict("records")

    def get_runs_by_trial(self, trial_id: int) -> List[Dict]:
        """All runs for a trial, oldest → newest."""
        df = self.runs_df[self.runs_df["trial_id"]
                          == trial_id].sort_values("created_at")
        return df.to_dict("records")

    @lru_cache(maxsize=32)
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """High-level KPIs used by the dashboard. Cached for speed."""
        total_experiments = int(len(self.experiments_df))
        total_trials = int(len(self.trials_df))
        total_runs = int(len(self.runs_df))

        # Total cost is straight from runs
        total_cost = float(self.runs_df["costs"].sum())

        # Accuracy is defined on finished trials only
        finished_mask = self.trials_df["status"] == TrialStatus.FINISHED.value
        avg_accuracy = float(
            self.trials_df.loc[finished_mask, "accuracy"].mean())

        avg_latency_ms = float(self.runs_df["latency_ms"].mean())

        active_trials = int(self.trials_df["status"].isin(
            [TrialStatus.PENDING.value, TrialStatus.RUNNING.value]).sum()
        )
        failed_trials = int(
            (self.trials_df["status"] == TrialStatus.FAILED.value).sum())

        success_rate = float(
            (self.trials_df["status"] == TrialStatus.FINISHED.value).sum()
            / max(total_trials, 1) * 100.0
        )

        # NaNs → sane defaults
        kpis = {
            "total_experiments": total_experiments,
            "total_trials": total_trials,
            "total_runs": total_runs,
            "total_cost": total_cost if pd.notna(total_cost) else 0.0,
            "avg_accuracy": avg_accuracy if pd.notna(avg_accuracy) else None,
            "avg_latency_ms": avg_latency_ms if pd.notna(avg_latency_ms) else None,
            "active_trials": active_trials,
            "failed_trials": failed_trials,
            "success_rate": success_rate if pd.notna(success_rate) else 0.0,
        }
        return kpis

    def get_cost_by_experiment(self) -> List[Dict]:
        """Cost breakdown by experiment (sum of runs, via trial rollup)."""
        # trials already contains total_cost and run_count from _precompute_aggregations
        merged = self.trials_df.merge(
            self.experiments_df[["id", "name"]], left_on="experiment_id", right_on="id", how="left"
        )

        grouped = (
            merged.groupby(["experiment_id", "name"], as_index=False)
            .agg(total_cost=("total_cost", "sum"), run_count=("run_count", "sum"))
        )

        total_cost = float(grouped["total_cost"].sum()) or 0.0

        result = []
        for _, row in grouped.iterrows():
            cost = float(row["total_cost"])
            result.append({
                "experiment_id": int(row["experiment_id"]),
                "experiment_name": row["name"],
                "total_cost": cost,
                "percentage": float(cost / total_cost * 100.0) if total_cost > 0 else 0.0,
                "run_count": int(row["run_count"]),
            })

        # Highest spend first
        return sorted(result, key=lambda x: x["total_cost"], reverse=True)

    def get_daily_costs(self, days: int = 30) -> List[Dict]:
        """Daily cost time series.
        - Date is derived from run timestamps.
        - run_count = number of runs that day.
        - experiment_count = number of distinct experiments that had runs that day.
        """
        df_runs = self.runs_df.copy()
        df_runs["date"] = df_runs["created_at"].dt.date

        # Pull experiment_id onto runs (via trials) to count unique experiments per day
        tri_cols = ["id", "experiment_id"]
        df = df_runs.merge(
            self.trials_df[tri_cols], left_on="trial_id", right_on="id", how="left")

        daily = (
            df.groupby("date", as_index=False)
            .agg(
                total_cost=("costs", "sum"),
                # id_x = runs.id after merge
                run_count=("id_x", "count"),
                experiment_count=("experiment_id", "nunique"),
            )
        )

        daily = daily.sort_values("date")
        out = [
            {
                "date": pd.Timestamp(d).strftime("%Y-%m-%d"),
                "total_cost": float(c),
                "run_count": int(r),
                "experiment_count": int(e),
            }
            for d, c, r, e in zip(daily["date"], daily["total_cost"], daily["run_count"], daily["experiment_count"])
        ]
        return out[-days:]  # last N days (already sorted)

    def search(self, query: str) -> Dict[str, List[Dict]]:
        """Lightweight search across experiments and trials."""
        q = str(query or "").lower()

        # Experiments: name / project_id
        e_mask = (
            self.experiments_df["name"].astype(
                "string").str.lower().str.contains(q, na=False)
            | self.experiments_df["project_id"].astype("string").str.lower().str.contains(q, na=False)
        )
        experiments = self.experiments_df.loc[e_mask].head(
            10).to_dict("records")

        # Trials: by status string (pending/running/finished/failed)
        t_mask = self.trials_df["status"].astype(
            "string").str.lower().str.contains(q, na=False)
        trials = self.trials_df.loc[t_mask].head(10).to_dict("records")

        return {"experiments": experiments, "trials": trials}

    def get_accuracy_curve(self, experiment_id: int) -> List[Dict]:
        """Accuracy curve for finished trials within an experiment (sorted by time)."""
        tri = self.trials_df[
            (self.trials_df["experiment_id"] == experiment_id)
            & (self.trials_df["status"] == TrialStatus.FINISHED.value)
            & (self.trials_df["accuracy"].notna())
        ].copy()

        tri = tri.sort_values("created_at")
        return [
            {
                "trial_id": int(row["id"]),
                "timestamp": pd.Timestamp(row["created_at"]).isoformat(),
                "accuracy": float(row["accuracy"]),
                "status": row["status"],
            }
            for _, row in tri.iterrows()
        ]


# Global instance (kept for your current imports)
data_manager = DataManager()
