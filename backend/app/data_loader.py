"""
CSV Data Loader with in-memory caching and efficient querying
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from functools import lru_cache
import logging

from app.config import settings
from app.models import TrialStatus

logger = logging.getLogger(__name__)


class DataManager:
    """
    Manages CSV data loading and provides efficient querying interface.
    Demonstrates good architecture despite simple data source.
    """

    def __init__(self):
        self.experiments_df: Optional[pd.DataFrame] = None
        self.trials_df: Optional[pd.DataFrame] = None
        self.runs_df: Optional[pd.DataFrame] = None
        self._initialized = False

    def initialize(self) -> None:
        """Load all CSV files into memory on startup"""
        try:
            logger.info("Loading CSV data into memory...")

            # Load experiments
            self.experiments_df = pd.read_csv(settings.experiments_path)
            self.experiments_df['created_at'] = pd.to_datetime(
                self.experiments_df['created_at'],
                format='%Y-%m-%d %H:%M:%S',
                errors='coerce'
            )
            self.experiments_df['is_del'] = self.experiments_df.get(
                'is_del', False).fillna(False)

            # Load trials
            self.trials_df = pd.read_csv(settings.trials_path)
            self.trials_df['created_at'] = pd.to_datetime(
                self.trials_df['created_at'],
                format='%d/%m/%Y %H:%M',
                errors='coerce'
            )
            # Clean up column names
            if 'duration(s)' in self.trials_df.columns:
                self.trials_df['duration_seconds'] = self.trials_df['duration(s)']

            # Load runs
            self.runs_df = pd.read_csv(settings.runs_path)
            self.runs_df['created_at'] = pd.to_datetime(
                self.runs_df['created_at'],
                format='%d/%m/%Y %H:%M',
                errors='coerce'
            )
            # Clean up column names
            if 'latency(ms)' in self.runs_df.columns:
                self.runs_df['latency_ms'] = self.runs_df['latency(ms)']

            # Create indices for faster lookups
            self._create_indices()

            # Precompute aggregations
            self._precompute_aggregations()

            self._initialized = True
            logger.info(f"Data loaded successfully: {len(self.experiments_df)} experiments, "
                        f"{len(self.trials_df)} trials, {len(self.runs_df)} runs")

        except Exception as e:
            logger.error(f"Failed to load CSV data: {e}")
            raise

    def _create_indices(self) -> None:
        """Create indices for faster lookups"""
        if self.experiments_df is not None:
            self.experiments_df.set_index('id', drop=False, inplace=True)
        if self.trials_df is not None:
            self.trials_df.set_index('id', drop=False, inplace=True)
        if self.runs_df is not None and 'id' in self.runs_df.columns:
            self.runs_df.set_index('id', drop=False, inplace=True)

    def _precompute_aggregations(self) -> None:
        """Precompute common aggregations for performance"""
        # Trial aggregations
        if self.runs_df is not None and self.trials_df is not None:
            trial_aggs = self.runs_df.groupby('trial_id').agg({
                'costs': 'sum',
                'tokens': 'sum',
                'latency_ms': 'mean',
                'trial_id': 'count'
            }).rename(columns={'trial_id': 'run_count'})

            self.trials_df = self.trials_df.merge(
                trial_aggs,
                left_on='id',
                right_index=True,
                how='left'
            )
            self.trials_df.fillna(
                {'costs': 0, 'tokens': 0, 'run_count': 0}, inplace=True)

        # Experiment aggregations
        if self.trials_df is not None and self.experiments_df is not None:
            exp_aggs = self.trials_df.groupby('experiment_id').agg({
                'accuracy': 'mean',
                'costs': 'sum',
                'experiment_id': 'count'
            }).rename(columns={'experiment_id': 'trial_count'})

            self.experiments_df = self.experiments_df.merge(
                exp_aggs,
                left_on='id',
                right_index=True,
                how='left'
            )
            self.experiments_df.fillna(
                {'costs': 0, 'trial_count': 0}, inplace=True)

    # ============= Query Methods =============

    def get_experiments(
        self,
        offset: int = 0,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> Tuple[List[Dict], int]:
        """Get paginated experiments with filters"""
        df = self.experiments_df.copy()

        # Apply filters
        if filters:
            if filters.get('name'):
                df = df[df['name'].str.contains(
                    filters['name'], case=False, na=False)]
            if filters.get('project_id'):
                df = df[df['project_id'] == filters['project_id']]
            if filters.get('created_after'):
                df = df[df['created_at'] >= filters['created_after']]
            if filters.get('created_before'):
                df = df[df['created_at'] <= filters['created_before']]

        # Sort
        ascending = sort_order == 'asc'
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=ascending)

        # Paginate
        total = len(df)
        df = df.iloc[offset:offset + limit]

        return df.to_dict('records'), total

    def get_experiment_by_id(self, experiment_id: int) -> Optional[Dict]:
        """Get single experiment by ID"""
        if experiment_id in self.experiments_df.index:
            return self.experiments_df.loc[experiment_id].to_dict()
        return None

    def get_trials_by_experiment(
        self,
        experiment_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict]:
        """Get all trials for an experiment"""
        df = self.trials_df[self.trials_df['experiment_id'] == experiment_id]

        if status_filter:
            df = df[df['status'] == status_filter]

        # Sort by created_at for accuracy curve
        df = df.sort_values('created_at')

        return df.to_dict('records')

    def get_runs_by_trial(self, trial_id: int) -> List[Dict]:
        """Get all runs for a trial"""
        df = self.runs_df[self.runs_df['trial_id'] == trial_id]
        df = df.sort_values('created_at')
        return df.to_dict('records')

    @lru_cache(maxsize=32)
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics with caching"""
        stats = {
            'total_experiments': len(self.experiments_df),
            'total_trials': len(self.trials_df),
            'total_runs': len(self.runs_df),
            'total_cost': float(self.runs_df['costs'].sum()),
            'avg_accuracy': float(
                self.trials_df[self.trials_df['status']
                               == 'finished']['accuracy'].mean()
            ),
            'avg_latency_ms': float(self.runs_df['latency_ms'].mean()),
            'active_trials': int(
                self.trials_df[self.trials_df['status'].isin(
                    ['pending', 'running'])].shape[0]
            ),
            'failed_trials': int(
                self.trials_df[self.trials_df['status'] == 'failed'].shape[0]
            ),
            'success_rate': float(
                self.trials_df[self.trials_df['status'] == 'finished'].shape[0] /
                max(len(self.trials_df), 1) * 100
            )
        }

        # Handle NaN values
        for key, value in stats.items():
            if pd.isna(value):
                stats[key] = 0 if 'total' in key or 'count' in key else None

        return stats

    def get_cost_by_experiment(self) -> List[Dict]:
        """Get cost breakdown by experiment"""
        # Merge to get experiment names and costs
        merged = self.trials_df.merge(
            self.experiments_df[['id', 'name']],
            left_on='experiment_id',
            right_on='id'
        )

        # Group by experiment
        grouped = merged.groupby(['experiment_id', 'name']).agg({
            'costs': 'sum',
            'run_count': 'sum'
        }).reset_index()

        total_cost = grouped['costs'].sum()

        # Calculate percentages
        result = []
        for _, row in grouped.iterrows():
            result.append({
                'experiment_id': int(row['experiment_id']),
                'experiment_name': row['name'],
                'total_cost': float(row['costs']),
                'percentage': float(row['costs'] / total_cost * 100) if total_cost > 0 else 0,
                'run_count': int(row['run_count'])
            })

        return sorted(result, key=lambda x: x['total_cost'], reverse=True)

    def get_daily_costs(self, days: int = 30) -> List[Dict]:
        """Get daily cost aggregation"""
        # Create date column
        df = self.runs_df.copy()
        df['date'] = df['created_at'].dt.date

        # Group by date
        daily = df.groupby('date').agg({
            'costs': 'sum',
            'trial_id': 'nunique',
            'tokens': 'sum'
        }).reset_index()

        daily.columns = ['date', 'total_cost',
                         'experiment_count', 'total_tokens']

        # Convert to list of dicts
        result = []
        for _, row in daily.iterrows():
            result.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'total_cost': float(row['total_cost']),
                # Using tokens as proxy for run count
                'run_count': int(row['total_tokens']),
                'experiment_count': int(row['experiment_count'])
            })

        return result[-days:]  # Return last N days

    def search(self, query: str) -> Dict[str, List[Dict]]:
        """Full-text search across all entities"""
        query_lower = query.lower()

        # Search experiments
        exp_mask = (
            self.experiments_df['name'].str.lower().str.contains(query_lower, na=False) |
            self.experiments_df['project_id'].str.lower(
            ).str.contains(query_lower, na=False)
        )
        matching_experiments = self.experiments_df[exp_mask].head(
            10).to_dict('records')

        # Search trials by status
        trial_mask = self.trials_df['status'].str.lower(
        ).str.contains(query_lower, na=False)
        matching_trials = self.trials_df[trial_mask].head(
            10).to_dict('records')

        return {
            'experiments': matching_experiments,
            'trials': matching_trials
        }

    def get_accuracy_curve(self, experiment_id: int) -> List[Dict]:
        """Get accuracy curve data for an experiment"""
        trials = self.trials_df[
            (self.trials_df['experiment_id'] == experiment_id) &
            (self.trials_df['status'] == 'finished') &
            (self.trials_df['accuracy'].notna())
        ].copy()

        trials = trials.sort_values('created_at')

        result = []
        for _, trial in trials.iterrows():
            result.append({
                'trial_id': int(trial['id']),
                'timestamp': trial['created_at'].isoformat(),
                'accuracy': float(trial['accuracy']),
                'status': trial['status']
            })

        return result


# Global instance
data_manager = DataManager()
