from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "SCIE용" / "data" / "15_g1_g2_g3_g4_retrieval_results.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "SCIE용" / "data" / "31_g3_g4_paired_bootstrap_ci.csv"


def rank_features(ranks: np.ndarray) -> dict[str, np.ndarray]:
    missing = np.isnan(ranks)
    return {
        "Image Recall@1": np.where(missing, 0.0, ranks <= 1).astype(float),
        "Image Recall@5": np.where(missing, 0.0, ranks <= 5).astype(float),
        "Image Recall@10": np.where(missing, 0.0, ranks <= 10).astype(float),
        "Image MRR": np.where(missing, 0.0, 1.0 / ranks),
    }


def paired_bootstrap(
    differences: np.ndarray,
    *,
    resamples: int,
    seed: int,
    batch_size: int = 10_000,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    samples = np.empty(resamples, dtype=float)
    count = len(differences)
    offset = 0
    while offset < resamples:
        size = min(batch_size, resamples - offset)
        indices = rng.integers(0, count, size=(size, count))
        samples[offset : offset + size] = differences[indices].mean(axis=1)
        offset += size
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return float(lower), float(upper)


def evaluate(input_path: Path, *, resamples: int, seed: int) -> list[dict[str, object]]:
    frame = pd.read_csv(input_path, encoding="utf-8-sig")
    g3_ranks = pd.to_numeric(frame["G3 이미지 정답 순위"], errors="coerce").to_numpy(float)
    g4_ranks = pd.to_numeric(frame["G4 이미지 정답 순위"], errors="coerce").to_numpy(float)
    if len(g3_ranks) != len(g4_ranks):
        raise ValueError("G3 and G4 rank arrays have different lengths")

    g3_features = rank_features(g3_ranks)
    g4_features = rank_features(g4_ranks)
    rows: list[dict[str, object]] = []
    for index, metric in enumerate(g3_features):
        g3 = g3_features[metric]
        g4 = g4_features[metric]
        differences = g4 - g3
        lower, upper = paired_bootstrap(
            differences,
            resamples=resamples,
            seed=seed + index,
        )
        rows.append(
            {
                "metric": metric,
                "query_count": len(differences),
                "g3_value": float(g3.mean()),
                "g4_value": float(g4.mean()),
                "paired_difference": float(differences.mean()),
                "ci_95_lower": lower,
                "ci_95_upper": upper,
                "improved_queries": int((differences > 0).sum()),
                "worsened_queries": int((differences < 0).sum()),
                "tied_queries": int((differences == 0).sum()),
                "bootstrap_resamples": resamples,
                "random_seed": seed + index,
            }
        )
    return rows


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Paired bootstrap intervals for G3-G4 image retrieval metrics")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resamples", type=int, default=200_000)
    parser.add_argument("--seed", type=int, default=20_260_810)
    args = parser.parse_args()

    rows = evaluate(args.input, resamples=args.resamples, seed=args.seed)
    write_csv(rows, args.output)
    print(args.output)
    for row in rows:
        print(
            f"{row['metric']}: diff={row['paired_difference']:.6f}, "
            f"95% CI [{row['ci_95_lower']:.6f}, {row['ci_95_upper']:.6f}]"
        )


if __name__ == "__main__":
    main()
