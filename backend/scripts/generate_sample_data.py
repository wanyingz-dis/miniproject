"""
Generate sample CSV data for testing 
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)


def generate_experiments(n=4):
    """Generate experiments data"""
    data = []
    projects = ["project_a", "project_b", "project_c"]

    for i in range(1, n + 1):
        data.append(
            {
                "id": i,
                "experiment_name": f"exp-{i}",
                "project_id": random.choice(projects),
                "created_at": (
                    datetime.now() - timedelta(days=random.randint(1, 30))
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "is_del": False,
            }
        )

    return pd.DataFrame(data)


def generate_trials(experiments_df, trials_per_exp=3):
    """Generate trials data"""
    data = []
    trial_id = 1
    statuses = ["finished", "finished", "finished", "failed", "pending"]

    for exp_id in experiments_df["id"]:
        n_trials = random.randint(2, trials_per_exp + 2)
        for _ in range(n_trials):
            status = random.choice(statuses)
            accuracy = random.uniform(0.3, 0.95) if status == "finished" else None
            duration = (
                random.randint(1000, 100000)
                if status in ["finished", "failed"]
                else None
            )

            data.append(
                {
                    "id": trial_id,
                    "experiment_id": exp_id,
                    "status": status,
                    "created_at": (
                        datetime.now() - timedelta(hours=random.randint(1, 500))
                    ).strftime("%d/%m/%Y %H:%M"),
                    "accuracy": accuracy,
                    "duration(s)": duration,
                }
            )
            trial_id += 1

    return pd.DataFrame(data)


def generate_runs(trials_df, runs_per_trial=5):
    """Generate runs data"""
    data = []
    run_id = 1

    for trial_id in trials_df["id"]:
        n_runs = random.randint(1, runs_per_trial + 3)
        for _ in range(n_runs):
            tokens = random.randint(100, 500000)
            # Cost correlates with tokens
            base_cost = tokens * 0.00001
            cost = base_cost * random.uniform(0.8, 1.2)

            data.append(
                {
                    "id": run_id,
                    "trial_id": trial_id,
                    "tokens": tokens,
                    "costs": round(cost, 2),
                    "latency(ms)": random.randint(10, 3000),
                    "created_at": (
                        datetime.now() - timedelta(hours=random.randint(1, 400))
                    ).strftime("%d/%m/%Y %H:%M"),
                }
            )
            run_id += 1

    return pd.DataFrame(data)


def main():
    """Generate all sample data files"""
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)

    print("Generating sample data...")

    # Generate data
    experiments_df = generate_experiments(4)
    trials_df = generate_trials(experiments_df, 3)
    runs_df = generate_runs(trials_df, 5)

    # Save to CSV
    experiments_df.to_csv("data/experiments.csv", index=False)
    trials_df.to_csv("data/trials.csv", index=False)
    runs_df.to_csv("data/runs.csv", index=False)

    print("Generated:")
    print(f"  - {len(experiments_df)} experiments")
    print(f"  - {len(trials_df)} trials")
    print(f"  - {len(runs_df)} runs")
    print("\nFiles saved to data/ directory")

    # Print sample statistics
    total_cost = runs_df["costs"].sum()
    avg_accuracy = trials_df[trials_df["status"] == "finished"]["accuracy"].mean()

    print("\nSample Statistics:")
    print(f"  Total cost: ${total_cost:.2f}")
    print(f"  Average accuracy: {avg_accuracy:.2%}")
    print(f"  Success rate: {(trials_df['status'] == 'finished').mean():.2%}")


if __name__ == "__main__":
    main()
