import csv
import json
import pickle
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import SCIE_DIR  # noqa: E402


OUTPUT_DIR = SCIE_DIR / "weight_optimization"
PAIR_CACHE_PATH = OUTPUT_DIR / "siglip_pair_scores.json"
FEATURE_CACHE_PATH = OUTPUT_DIR / "retrieval_feature_cache.pkl"
BEST_CONFIG_PATH = OUTPUT_DIR / "best_weights.json"
G3_SEARCH_PATH = OUTPUT_DIR / "g3_search_top100.csv"
G4_SEARCH_PATH = OUTPUT_DIR / "g4_search_top100.csv"
QUESTION_RANKS_PATH = OUTPUT_DIR / "best_question_ranks.csv"
REPORT_PATH = OUTPUT_DIR / "weight_optimization_report.md"

SEED = 20260716
FOLD_COUNT = 5
IMAGE_LIMIT = 10
MAPPING_TOP_N = 2
MAPPING_KEEP_THRESHOLD = 0.40

CURRENT_MAPPING_ALPHA = 0.45
CURRENT_G3_WEIGHTS = np.asarray([0.42, 0.18, 0.28, 0.09, 0.03], dtype=np.float32)
CURRENT_SOURCE_COEFFICIENT = 0.02
FEATURE_NAMES = ["image_search", "text_rank", "page", "mapping", "diagram_confidence"]

# The unconstrained search is retained as a diagnostic. These rounded settings
# are the methodologically conservative recommendation used for reporting.
RECOMMENDED_G3_CONFIG = {
    "semantic_mode": "robust_cosine",
    "bbox_weight": 0.0,
    "siglip_weight": 1.0,
    "weights": [0.25, 0.15, 0.50, 0.05, 0.05],
    "source_coefficient": 0.0,
}
RECOMMENDED_G4_CONFIG = {
    "min_score": 0.45,
    "min_margin": 0.03,
    "map_weights": [0.50, 0.10, 0.40],
    "query_scale": 0.0,
    "rank_scale": 0.0,
    "context_coefficient": 0.50,
    "page_prior_coefficient": 0.25,
    "rank_window": 120,
}


def load_caches():
    if not PAIR_CACHE_PATH.exists():
        raise FileNotFoundError(f"Missing pair cache: {PAIR_CACHE_PATH}")
    if not FEATURE_CACHE_PATH.exists():
        raise FileNotFoundError(f"Missing retrieval feature cache: {FEATURE_CACHE_PATH}")
    pair_cache = json.loads(PAIR_CACHE_PATH.read_text(encoding="utf-8"))
    with FEATURE_CACHE_PATH.open("rb") as handle:
        feature_cache = pickle.load(handle)
    return pair_cache, feature_cache


def metrics(ranks, indices=None):
    ranks = np.asarray(ranks, dtype=np.int16)
    if indices is not None:
        ranks = ranks[np.asarray(indices, dtype=np.int32)]
    total = max(1, len(ranks))
    reciprocal = np.where(ranks > 0, 1.0 / np.maximum(ranks, 1), 0.0)
    return {
        "r1": float(np.sum((ranks > 0) & (ranks <= 1)) / total),
        "r5": float(np.sum((ranks > 0) & (ranks <= 5)) / total),
        "r10": float(np.sum((ranks > 0) & (ranks <= 10)) / total),
        "mrr": float(np.mean(reciprocal)),
    }


def metric_key(metric):
    return (metric["mrr"], metric["r5"], metric["r1"], metric["r10"])


def percent(value):
    return f"{100.0 * value:.1f}%"


def make_folds(records):
    rng = random.Random(SEED)
    strata = defaultdict(list)
    for index, record in enumerate(records):
        strata[(record["category"], record["question_type"])].append(index)

    folds = [[] for _ in range(FOLD_COUNT)]
    for key in sorted(strata, key=str):
        indices = strata[key]
        rng.shuffle(indices)
        for index in indices:
            smallest = min(range(FOLD_COUNT), key=lambda fold: (len(folds[fold]), fold))
            folds[smallest].append(index)
    return [sorted(fold) for fold in folds]


def semantic_limits(pair_cache):
    values = np.asarray(
        [
            pair["siglip_cosine"]
            for chunk in pair_cache["chunks"]
            for pair in chunk.get("pairs", [])
        ],
        dtype=np.float32,
    )
    return float(np.percentile(values, 5)), float(np.percentile(values, 95))


def semantic_score(pair, mode, pair_count, cosine_low, cosine_high):
    if mode == "robust_cosine":
        return float(np.clip((pair["siglip_cosine"] - cosine_low) / (cosine_high - cosine_low), 0.0, 1.0))
    if mode == "sigmoid_probability":
        return float(pair["siglip_probability"])
    if mode == "relative_softmax":
        return float(pair["siglip_relative_softmax"])
    if mode == "legacy_relative":
        return 0.0 if pair_count == 1 else float(pair["siglip_relative_softmax"])
    raise ValueError(f"Unsupported semantic score mode: {mode}")


def build_mapping_features(feature_cache, pair_cache, semantic_mode, bbox_weight, cosine_low, cosine_high):
    records = feature_cache["records"]
    image_names = feature_cache["image_names"]
    name_to_index = {name: index for index, name in enumerate(image_names)}
    pair_by_chunk = {chunk["chunk_id"]: chunk.get("pairs", []) for chunk in pair_cache["chunks"]}
    question_count = len(records)
    image_count = len(image_names)

    feature_tensor = np.zeros((question_count, image_count, len(FEATURE_NAMES)), dtype=np.float32)
    source_count = np.zeros((question_count, image_count), dtype=np.int16)
    base_mask = np.zeros((question_count, image_count), dtype=bool)
    pair_semantic = np.zeros((question_count, image_count), dtype=np.float32)

    for question_index, record in enumerate(records):
        image = record["image"]
        feature_tensor[question_index, :, 0] = image["image_search"]
        feature_tensor[question_index, :, 2] = image["page_score"]
        feature_tensor[question_index, :, 4] = image["diagram_confidence"]
        source_count[question_index] = image["base_source_count"]
        base_mask[question_index] = image["base_mask"]
        mapping_sources = [set() for _ in range(image_count)]

        for retrieved in image["retrieved_chunks"]:
            pairs = pair_by_chunk.get(retrieved["chunk_id"], [])
            pair_count = len(pairs)
            scored = []
            for pair in pairs:
                semantic = semantic_score(pair, semantic_mode, pair_count, cosine_low, cosine_high)
                hybrid = (bbox_weight * float(pair["distance_score"])) + ((1.0 - bbox_weight) * semantic)
                if float(pair["adjusted_distance"]) < 300.0 or semantic >= MAPPING_KEEP_THRESHOLD:
                    scored.append((hybrid, -float(pair["adjusted_distance"]), semantic, pair))
            scored.sort(reverse=True, key=lambda item: (item[0], item[1]))

            for hybrid, _, semantic, pair in scored[:MAPPING_TOP_N]:
                image_index = name_to_index[pair["file_name"]]
                base_mask[question_index, image_index] = True
                feature_tensor[question_index, image_index, 1] = max(
                    feature_tensor[question_index, image_index, 1],
                    float(retrieved["rank_score"]),
                )
                feature_tensor[question_index, image_index, 3] = max(
                    feature_tensor[question_index, image_index, 3],
                    hybrid,
                )
                pair_semantic[question_index, image_index] = max(
                    pair_semantic[question_index, image_index],
                    semantic,
                )
                mapping_sources[image_index].add(int(retrieved["rank"]))

        source_count[question_index] += np.asarray(
            [len(values) for values in mapping_sources],
            dtype=np.int16,
        )

    return {
        "features": feature_tensor,
        "source_count": source_count,
        "base_mask": base_mask,
        "pair_semantic": pair_semantic,
    }


def base_scores(mapping_data, weights, source_coefficient, legacy_mixed_siglip=False):
    features = mapping_data["features"].copy()
    if legacy_mixed_siglip:
        features[:, :, 4] = np.maximum(features[:, :, 4], mapping_data["pair_semantic"])
    scores = np.einsum("qif,f->qi", features, np.asarray(weights, dtype=np.float32))
    scores += source_coefficient * np.minimum(4, mapping_data["source_count"])
    return scores


def ranks_from_scores(scores, masks, expected_indices):
    ranks = np.zeros(len(expected_indices), dtype=np.int16)
    for question_index, expected_index in enumerate(expected_indices):
        valid = np.flatnonzero(masks[question_index])
        if expected_index not in valid:
            continue
        valid_scores = scores[question_index, valid]
        order = valid[np.argsort(-valid_scores, kind="stable")]
        positions = np.flatnonzero(order == expected_index)
        if positions.size and positions[0] < IMAGE_LIMIT:
            ranks[question_index] = int(positions[0] + 1)
    return ranks


def random_weight_vectors(rng, count):
    presets = [
        CURRENT_G3_WEIGHTS,
        np.full(5, 0.2, dtype=np.float32),
        np.asarray([0.50, 0.15, 0.20, 0.10, 0.05], dtype=np.float32),
        np.asarray([0.35, 0.15, 0.30, 0.15, 0.05], dtype=np.float32),
        np.asarray([0.35, 0.20, 0.20, 0.20, 0.05], dtype=np.float32),
    ]
    for index in range(5):
        vector = np.zeros(5, dtype=np.float32)
        vector[index] = 1.0
        presets.append(vector)

    seen = set()
    results = []
    for vector in presets + [rng.dirichlet(np.full(5, 1.5)).astype(np.float32) for _ in range(count)]:
        vector = vector / max(float(vector.sum()), 1e-12)
        key = tuple(round(float(value), 4) for value in vector)
        if key in seen:
            continue
        seen.add(key)
        results.append(vector)
    return results


def vectorized_best(rank_matrix, indices):
    selected = rank_matrix[:, np.asarray(indices, dtype=np.int32)]
    valid = selected > 0
    mrr = np.mean(np.where(valid, 1.0 / np.maximum(selected, 1), 0.0), axis=1)
    r1 = np.mean(valid & (selected <= 1), axis=1)
    r5 = np.mean(valid & (selected <= 5), axis=1)
    r10 = np.mean(valid & (selected <= 10), axis=1)
    order = np.lexsort((r10, r1, r5, mrr))
    return int(order[-1])


def cross_validated_selection(rank_matrix, configs, folds):
    all_indices = set(range(rank_matrix.shape[1]))
    cv_ranks = np.zeros(rank_matrix.shape[1], dtype=np.int16)
    fold_results = []
    for fold_index, validation in enumerate(folds):
        training = sorted(all_indices - set(validation))
        best_index = vectorized_best(rank_matrix, training)
        cv_ranks[validation] = rank_matrix[best_index, validation]
        fold_results.append(
            {
                "fold": fold_index + 1,
                "config_index": best_index,
                "config": configs[best_index],
                "train_metrics": metrics(rank_matrix[best_index], training),
                "validation_metrics": metrics(rank_matrix[best_index], validation),
                "validation_question_count": len(validation),
            }
        )
    global_index = vectorized_best(rank_matrix, list(range(rank_matrix.shape[1])))
    return {
        "cv_ranks": cv_ranks,
        "cv_metrics": metrics(cv_ranks),
        "folds": fold_results,
        "global_index": global_index,
        "global_config": configs[global_index],
        "global_ranks": rank_matrix[global_index],
        "global_metrics": metrics(rank_matrix[global_index]),
    }


def g3_search(feature_cache, pair_cache, folds):
    rng = np.random.default_rng(SEED)
    cosine_low, cosine_high = semantic_limits(pair_cache)
    expected_indices = np.asarray(
        [record["expected_image_index"] for record in feature_cache["records"]],
        dtype=np.int32,
    )
    semantic_modes = ["robust_cosine", "sigmoid_probability", "relative_softmax"]
    bbox_weights = [round(value, 1) for value in np.linspace(0.0, 1.0, 11)]
    weight_vectors = random_weight_vectors(rng, 180)
    source_coefficients = [0.0, 0.01, 0.02]
    mapping_cache = {}
    configs = []
    rank_rows = []

    for semantic_mode in semantic_modes:
        for bbox_weight in bbox_weights:
            key = (semantic_mode, bbox_weight)
            mapping_data = build_mapping_features(
                feature_cache,
                pair_cache,
                semantic_mode,
                bbox_weight,
                cosine_low,
                cosine_high,
            )
            mapping_cache[key] = mapping_data
            for weights in weight_vectors:
                for source_coefficient in source_coefficients:
                    scores = base_scores(mapping_data, weights, source_coefficient)
                    ranks = ranks_from_scores(scores, mapping_data["base_mask"], expected_indices)
                    configs.append(
                        {
                            "semantic_mode": semantic_mode,
                            "bbox_weight": bbox_weight,
                            "siglip_weight": round(1.0 - bbox_weight, 1),
                            "weights": [round(float(value), 6) for value in weights],
                            "source_coefficient": source_coefficient,
                        }
                    )
                    rank_rows.append(ranks)
            print(f"[G3 search] {semantic_mode} BBox={bbox_weight:.1f}", flush=True)

    rank_matrix = np.asarray(rank_rows, dtype=np.int16)
    selection = cross_validated_selection(rank_matrix, configs, folds)

    constrained_indices = [
        index
        for index, config in enumerate(configs)
        if config["semantic_mode"] == "robust_cosine"
        and max(config["weights"]) <= 0.60
        and config["weights"][3] >= 0.03
    ]
    constrained_selection = cross_validated_selection(
        rank_matrix[constrained_indices],
        [configs[index] for index in constrained_indices],
        folds,
    )

    legacy_mapping = build_mapping_features(
        feature_cache,
        pair_cache,
        "legacy_relative",
        CURRENT_MAPPING_ALPHA,
        cosine_low,
        cosine_high,
    )
    legacy_scores = base_scores(
        legacy_mapping,
        CURRENT_G3_WEIGHTS,
        CURRENT_SOURCE_COEFFICIENT,
        legacy_mixed_siglip=True,
    )
    legacy_ranks = ranks_from_scores(legacy_scores, legacy_mapping["base_mask"], expected_indices)

    best = selection["global_config"]
    best_mapping = mapping_cache[(best["semantic_mode"], best["bbox_weight"])]
    best_scores = base_scores(best_mapping, best["weights"], best["source_coefficient"])

    recommended_mapping = build_mapping_features(
        feature_cache,
        pair_cache,
        RECOMMENDED_G3_CONFIG["semantic_mode"],
        RECOMMENDED_G3_CONFIG["bbox_weight"],
        cosine_low,
        cosine_high,
    )
    recommended_scores = base_scores(
        recommended_mapping,
        RECOMMENDED_G3_CONFIG["weights"],
        RECOMMENDED_G3_CONFIG["source_coefficient"],
    )
    recommended_ranks = ranks_from_scores(
        recommended_scores,
        recommended_mapping["base_mask"],
        expected_indices,
    )

    isolated_mapping_rows = []
    for semantic_mode in semantic_modes:
        for bbox_weight in bbox_weights:
            mapping_data = mapping_cache[(semantic_mode, bbox_weight)]
            ranks = ranks_from_scores(
                base_scores(mapping_data, CURRENT_G3_WEIGHTS, CURRENT_SOURCE_COEFFICIENT),
                mapping_data["base_mask"],
                expected_indices,
            )
            isolated_mapping_rows.append(
                {
                    "semantic_mode": semantic_mode,
                    "bbox_weight": bbox_weight,
                    "siglip_weight": round(1.0 - bbox_weight, 1),
                    "metrics": metrics(ranks),
                }
            )

    return {
        "configs": configs,
        "rank_matrix": rank_matrix,
        "selection": selection,
        "constrained_selection": constrained_selection,
        "legacy_ranks": legacy_ranks,
        "legacy_metrics": metrics(legacy_ranks),
        "legacy_mapping": legacy_mapping,
        "best_mapping": best_mapping,
        "best_scores": best_scores,
        "recommended_config": dict(RECOMMENDED_G3_CONFIG),
        "recommended_mapping": recommended_mapping,
        "recommended_scores": recommended_scores,
        "recommended_ranks": recommended_ranks,
        "recommended_metrics": metrics(recommended_ranks),
        "isolated_mapping": isolated_mapping_rows,
        "cosine_low": cosine_low,
        "cosine_high": cosine_high,
    }


def base_rank_factors(base_scores_array, union_mask, stage_page, window):
    factors = np.zeros_like(base_scores_array, dtype=np.float32)
    for question_index in range(base_scores_array.shape[0]):
        valid = np.flatnonzero(union_mask[question_index])
        order = valid[np.argsort(-base_scores_array[question_index, valid], kind="stable")]
        for position, image_index in enumerate(order, start=1):
            if position <= window:
                factors[question_index, image_index] = 1.0 - ((position - 1) / max(1, window))
            elif stage_page[question_index, image_index] > 0:
                factors[question_index, image_index] = 0.35
    return factors


def random_stage_weights(rng, count):
    presets = [
        np.asarray([0.58, 0.27, 0.15], dtype=np.float32),
        np.asarray([0.55, 0.30, 0.15], dtype=np.float32),
        np.asarray([1 / 3, 1 / 3, 1 / 3], dtype=np.float32),
        np.asarray([0.70, 0.20, 0.10], dtype=np.float32),
        np.asarray([0.50, 0.30, 0.20], dtype=np.float32),
        np.asarray([0.40, 0.45, 0.15], dtype=np.float32),
    ]
    values = presets + [rng.dirichlet(np.full(3, 1.5)).astype(np.float32) for _ in range(count)]
    seen = set()
    results = []
    for value in values:
        value = value / max(float(value.sum()), 1e-12)
        key = tuple(round(float(item), 4) for item in value)
        if key not in seen:
            seen.add(key)
            results.append(value)
    return results


def g4_ranks_for_config(
    config,
    base_score_array,
    base_mask,
    union_mask,
    stage_query,
    stage_rank,
    stage_page,
    stage_keyword,
    stage_section,
    context_weights,
    classifier_scores,
    classifier_margins,
    expected_indices,
    rank_factor_by_window,
):
    map_weights = np.asarray(config["map_weights"], dtype=np.float32)
    map_score = (
        map_weights[0] * stage_page
        + map_weights[1] * stage_keyword
        + map_weights[2] * stage_section
    ) * context_weights[:, None]
    stage_score = np.maximum.reduce(
        [
            config["query_scale"] * stage_query,
            config["rank_scale"] * stage_rank,
            map_score,
        ]
    )
    rank_factor = rank_factor_by_window[config["rank_window"]]
    scores = base_score_array + (
        config["context_coefficient"] * stage_score * rank_factor
    ) + (config["page_prior_coefficient"] * stage_page)
    applied = (classifier_scores >= config["min_score"]) & (classifier_margins >= config["min_margin"])
    effective_scores = base_score_array.copy()
    effective_masks = base_mask.copy()
    effective_scores[applied] = scores[applied]
    effective_masks[applied] = union_mask[applied]
    return ranks_from_scores(effective_scores, effective_masks, expected_indices), applied


def g4_search(feature_cache, g3_result, folds):
    rng = np.random.default_rng(SEED + 1)
    records = feature_cache["records"]
    question_count = len(records)
    image_count = len(feature_cache["image_names"])
    expected_indices = np.asarray([record["expected_image_index"] for record in records], dtype=np.int32)
    best_g3 = g3_result["recommended_config"]
    mapping_data = g3_result["recommended_mapping"]
    base_score_array = base_scores(
        mapping_data,
        best_g3["weights"],
        best_g3["source_coefficient"],
    )
    base_mask = mapping_data["base_mask"]

    stage_query = np.stack([record["image"]["stage_query_score"] for record in records])
    stage_rank = np.stack([record["image"]["stage_rank_score"] for record in records])
    stage_page = np.stack([record["image"]["stage_page"] for record in records])
    stage_keyword = np.stack([record["image"]["stage_keyword"] for record in records])
    stage_section = np.stack([record["image"]["stage_section"] for record in records])
    stage_source = np.stack([record["image"]["stage_source_mask"] for record in records])
    stage_map = np.stack([record["image"]["stage_map_mask"] for record in records])
    union_mask = base_mask | stage_source | stage_map
    context_weights = np.asarray([record["stage_context_weight"] for record in records], dtype=np.float32)
    classifier_scores = np.asarray([record["classification"]["score"] for record in records], dtype=np.float32)
    classifier_margins = np.asarray([record["classification"]["margin"] for record in records], dtype=np.float32)
    rank_windows = [40, 80, 120]
    rank_factor_by_window = {
        window: base_rank_factors(base_score_array, union_mask, stage_page, window)
        for window in rank_windows
    }

    stage_weight_vectors = random_stage_weights(rng, 80)
    choices = {
        "min_score": [0.35, 0.40, 0.45, 0.50, 0.55, 0.60],
        "min_margin": [0.00, 0.01, 0.03, 0.05, 0.08, 0.10],
        "query_scale": [0.0, 0.25, 0.45, 0.60, 0.80],
        "rank_scale": [0.0, 0.25, 0.35, 0.50, 0.75],
        "context_coefficient": [0.0, 0.16, 0.24, 0.32, 0.40, 0.50],
        "page_prior_coefficient": [0.0, 0.10, 0.20, 0.25, 0.30],
        "rank_window": rank_windows,
    }
    current = {
        "min_score": 0.45,
        "min_margin": 0.03,
        "map_weights": [0.58, 0.27, 0.15],
        "query_scale": 0.45,
        "rank_scale": 0.35,
        "context_coefficient": 0.32,
        "page_prior_coefficient": 0.25,
        "rank_window": 80,
    }
    configs = [current]
    seen = {json.dumps(current, sort_keys=True)}
    for _ in range(3500):
        vector = stage_weight_vectors[int(rng.integers(0, len(stage_weight_vectors)))]
        config = {
            "min_score": float(rng.choice(choices["min_score"])),
            "min_margin": float(rng.choice(choices["min_margin"])),
            "map_weights": [round(float(value), 6) for value in vector],
            "query_scale": float(rng.choice(choices["query_scale"])),
            "rank_scale": float(rng.choice(choices["rank_scale"])),
            "context_coefficient": float(rng.choice(choices["context_coefficient"])),
            "page_prior_coefficient": float(rng.choice(choices["page_prior_coefficient"])),
            "rank_window": int(rng.choice(choices["rank_window"])),
        }
        key = json.dumps(config, sort_keys=True)
        if key not in seen:
            seen.add(key)
            configs.append(config)

    rank_rows = []
    applied_rows = []
    for index, config in enumerate(configs, start=1):
        ranks, applied = g4_ranks_for_config(
            config,
            base_score_array,
            base_mask,
            union_mask,
            stage_query,
            stage_rank,
            stage_page,
            stage_keyword,
            stage_section,
            context_weights,
            classifier_scores,
            classifier_margins,
            expected_indices,
            rank_factor_by_window,
        )
        rank_rows.append(ranks)
        applied_rows.append(applied)
        if index % 500 == 0 or index == len(configs):
            print(f"[G4 search] {index}/{len(configs)}", flush=True)

    rank_matrix = np.asarray(rank_rows, dtype=np.int16)
    selection = cross_validated_selection(rank_matrix, configs, folds)
    fixed_threshold_indices = [
        index
        for index, config in enumerate(configs)
        if config["min_score"] == RECOMMENDED_G4_CONFIG["min_score"]
        and config["min_margin"] == RECOMMENDED_G4_CONFIG["min_margin"]
    ]
    fixed_threshold_selection = cross_validated_selection(
        rank_matrix[fixed_threshold_indices],
        [configs[index] for index in fixed_threshold_indices],
        folds,
    )
    recommended_ranks, recommended_applied = g4_ranks_for_config(
        RECOMMENDED_G4_CONFIG,
        base_score_array,
        base_mask,
        union_mask,
        stage_query,
        stage_rank,
        stage_page,
        stage_keyword,
        stage_section,
        context_weights,
        classifier_scores,
        classifier_margins,
        expected_indices,
        rank_factor_by_window,
    )
    current_ranks = rank_matrix[0]

    legacy_base_scores = base_scores(
        g3_result["legacy_mapping"],
        CURRENT_G3_WEIGHTS,
        CURRENT_SOURCE_COEFFICIENT,
        legacy_mixed_siglip=True,
    )
    legacy_base_mask = g3_result["legacy_mapping"]["base_mask"]
    legacy_union_mask = legacy_base_mask | stage_source | stage_map
    legacy_rank_factors = {
        80: base_rank_factors(legacy_base_scores, legacy_union_mask, stage_page, 80)
    }
    legacy_current_ranks, legacy_current_applied = g4_ranks_for_config(
        current,
        legacy_base_scores,
        legacy_base_mask,
        legacy_union_mask,
        stage_query,
        stage_rank,
        stage_page,
        stage_keyword,
        stage_section,
        context_weights,
        classifier_scores,
        classifier_margins,
        expected_indices,
        legacy_rank_factors,
    )
    return {
        "configs": configs,
        "rank_matrix": rank_matrix,
        "selection": selection,
        "fixed_threshold_selection": fixed_threshold_selection,
        "current_ranks": current_ranks,
        "current_metrics": metrics(current_ranks),
        "legacy_current_ranks": legacy_current_ranks,
        "legacy_current_metrics": metrics(legacy_current_ranks),
        "legacy_current_applied": legacy_current_applied,
        "recommended_config": dict(RECOMMENDED_G4_CONFIG),
        "recommended_ranks": recommended_ranks,
        "recommended_metrics": metrics(recommended_ranks),
        "recommended_applied": recommended_applied,
        "base_score_array": base_score_array,
        "base_mask": base_mask,
        "union_mask": union_mask,
        "stage_arrays": {
            "query": stage_query,
            "rank": stage_rank,
            "page": stage_page,
            "keyword": stage_keyword,
            "section": stage_section,
            "context_weights": context_weights,
            "classifier_scores": classifier_scores,
            "classifier_margins": classifier_margins,
            "rank_factor_by_window": rank_factor_by_window,
            "expected_indices": expected_indices,
        },
    }


def text_ranks_for_config(records, config, applied):
    ranks = np.zeros(len(records), dtype=np.int16)
    weights = np.asarray(config["map_weights"], dtype=np.float32)
    for question_index, record in enumerate(records):
        text = record["text"]
        score = text["base_rank"].copy()
        if applied[question_index]:
            stage_score = (
                weights[0] * text["stage_page"]
                + weights[1] * text["stage_keyword"]
                + weights[2] * text["stage_section"]
            ) * record["stage_context_weight"]
            score += config["stage_coefficient"] * stage_score
        order = np.argsort(-score, kind="stable")[:IMAGE_LIMIT]
        relevant_positions = np.flatnonzero(text["relevance"][order])
        if relevant_positions.size:
            ranks[question_index] = int(relevant_positions[0] + 1)
    return ranks


def text_g4_search(feature_cache, g4_result, folds):
    rng = np.random.default_rng(SEED + 2)
    records = feature_cache["records"]
    applied = g4_result["recommended_applied"]
    weight_vectors = random_stage_weights(rng, 100)
    coefficients = [0.0, 0.10, 0.20, 0.28, 0.35, 0.45, 0.60]
    configs = []
    rank_rows = []
    for weights in weight_vectors:
        for coefficient in coefficients:
            config = {
                "map_weights": [round(float(value), 6) for value in weights],
                "stage_coefficient": coefficient,
            }
            configs.append(config)
            rank_rows.append(text_ranks_for_config(records, config, applied))
    rank_matrix = np.asarray(rank_rows, dtype=np.int16)
    selection = cross_validated_selection(rank_matrix, configs, folds)
    current_config = {"map_weights": [0.55, 0.30, 0.15], "stage_coefficient": 0.28}
    current_ranks = text_ranks_for_config(records, current_config, applied)
    return {
        "selection": selection,
        "current_config": current_config,
        "current_ranks": current_ranks,
        "current_metrics": metrics(current_ranks),
    }


def bootstrap_ci(ranks, metric_name, samples=3000):
    rng = np.random.default_rng(SEED + 3)
    ranks = np.asarray(ranks, dtype=np.int16)
    values = []
    for _ in range(samples):
        sample = ranks[rng.integers(0, len(ranks), len(ranks))]
        values.append(metrics(sample)[metric_name])
    low, high = np.percentile(values, [2.5, 97.5])
    return [float(low), float(high)]


def bootstrap_delta_ci(first, second, metric_name, samples=3000):
    rng = np.random.default_rng(SEED + 4)
    first = np.asarray(first, dtype=np.int16)
    second = np.asarray(second, dtype=np.int16)
    values = []
    for _ in range(samples):
        indices = rng.integers(0, len(first), len(first))
        values.append(metrics(second[indices])[metric_name] - metrics(first[indices])[metric_name])
    low, high = np.percentile(values, [2.5, 97.5])
    return [float(low), float(high)]


def g3_ablations(g3_result, feature_cache, pair_cache):
    best = g3_result["recommended_config"]
    mapping_data = g3_result["recommended_mapping"]
    expected = np.asarray([r["expected_image_index"] for r in feature_cache["records"]], dtype=np.int32)
    rows = []

    def add(label, weights, source_coefficient, data=mapping_data):
        ranks = ranks_from_scores(
            base_scores(data, weights, source_coefficient),
            data["base_mask"],
            expected,
        )
        rows.append({"label": label, "metrics": metrics(ranks), "ranks": ranks})

    add("Recommended G3", best["weights"], best["source_coefficient"])
    weights = np.asarray(best["weights"], dtype=np.float32)
    for index, name in enumerate(FEATURE_NAMES):
        ablated = weights.copy()
        ablated[index] = 0.0
        if ablated.sum() > 0:
            ablated /= ablated.sum()
        add(f"without {name}", ablated, best["source_coefficient"])
    add("without source bonus", weights, 0.0)

    cosine_low, cosine_high = g3_result["cosine_low"], g3_result["cosine_high"]
    for bbox_weight, label in [(1.0, "BBox only mapping"), (0.0, "SigLIP only mapping")]:
        data = build_mapping_features(
            feature_cache,
            pair_cache,
            best["semantic_mode"],
            bbox_weight,
            cosine_low,
            cosine_high,
        )
        add(label, weights, best["source_coefficient"], data=data)
    return rows


def g4_ablations(g4_result):
    best = dict(g4_result["recommended_config"])
    arrays = g4_result["stage_arrays"]
    rows = []

    def add(label, config):
        ranks, _ = g4_ranks_for_config(
            config,
            g4_result["base_score_array"],
            g4_result["base_mask"],
            g4_result["union_mask"],
            arrays["query"],
            arrays["rank"],
            arrays["page"],
            arrays["keyword"],
            arrays["section"],
            arrays["context_weights"],
            arrays["classifier_scores"],
            arrays["classifier_margins"],
            arrays["expected_indices"],
            arrays["rank_factor_by_window"],
        )
        rows.append({"label": label, "metrics": metrics(ranks), "ranks": ranks})

    add("Recommended G4", best)
    variants = [
        ("without stage evidence", {"context_coefficient": 0.0}),
        ("without page prior", {"page_prior_coefficient": 0.0}),
        ("without stage image query", {"query_scale": 0.0}),
        ("without stage rank", {"rank_scale": 0.0}),
        ("context map only", {"query_scale": 0.0, "rank_scale": 0.0}),
    ]
    for label, changes in variants:
        config = dict(best)
        config.update(changes)
        add(label, config)
    return rows


def top_search_rows(configs, rank_matrix, limit=100):
    rows = []
    for index, config in enumerate(configs):
        metric = metrics(rank_matrix[index])
        rows.append((metric_key(metric), config, metric))
    rows.sort(reverse=True, key=lambda item: item[0])
    return rows[:limit]


def write_search_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["rank", "config_json", "Image Recall@1", "Image Recall@5", "Image Recall@10", "Image MRR"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, (_, config, metric) in enumerate(rows, start=1):
            writer.writerow(
                {
                    "rank": rank,
                    "config_json": json.dumps(config, ensure_ascii=False, sort_keys=True),
                    "Image Recall@1": metric["r1"],
                    "Image Recall@5": metric["r5"],
                    "Image Recall@10": metric["r10"],
                    "Image MRR": metric["mrr"],
                }
            )


def metric_table_row(label, metric):
    return f"| {label} | {percent(metric['r1'])} | {percent(metric['r5'])} | {percent(metric['r10'])} | {metric['mrr']:.3f} |"


def write_outputs(feature_cache, pair_cache, folds, g3, g4, text_g4, g3_ablation, g4_ablation):
    g3_best = g3["recommended_config"]
    g4_best = g4["recommended_config"]
    text_best = text_g4["current_config"]
    records = feature_cache["records"]
    best_g3_ranks = g3["recommended_ranks"]
    best_g4_ranks = g4["recommended_ranks"]

    best_config = {
        "method": {
            "selection": "5-fold cross-validation; deployment values retuned on all 70 questions",
            "primary_metric": "Image MRR",
            "secondary_metric": "Image Recall@5",
            "random_seed": SEED,
            "warning": "The 70 questions are reused for cross-validation. A separate external test set is still required for confirmatory reporting.",
        },
        "score_normalization": {
            "siglip_mode": g3_best["semantic_mode"],
            "robust_cosine_percentiles": [g3["cosine_low"], g3["cosine_high"]],
        },
        "recommended": {
            "g3": g3_best,
            "g4": g4_best,
            "g4_text": text_best,
        },
        "unconstrained_performance_optimum": {
            "g3": g3["selection"]["global_config"],
            "g4": g4["selection"]["global_config"],
        },
        "cross_validation": {
            "g3_unconstrained": g3["selection"]["cv_metrics"],
            "g3_constrained": g3["constrained_selection"]["cv_metrics"],
            "g4_unconstrained": g4["selection"]["cv_metrics"],
            "g4_fixed_stage_threshold": g4["fixed_threshold_selection"]["cv_metrics"],
            "g4_text": text_g4["selection"]["cv_metrics"],
            "folds": [
                [records[index]["question_id"] for index in fold]
                for fold in folds
            ],
        },
    }
    BEST_CONFIG_PATH.write_text(json.dumps(best_config, ensure_ascii=False, indent=2), encoding="utf-8")

    write_search_csv(G3_SEARCH_PATH, top_search_rows(g3["configs"], g3["rank_matrix"]))
    write_search_csv(G4_SEARCH_PATH, top_search_rows(g4["configs"], g4["rank_matrix"]))

    fold_by_index = {}
    for fold_index, fold in enumerate(folds, start=1):
        for question_index in fold:
            fold_by_index[question_index] = fold_index
    with QUESTION_RANKS_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = [
            "question_id",
            "fold",
            "expected_image",
            "expected_stage",
            "predicted_stage",
            "stage_score",
            "stage_margin",
            "legacy_g3_rank",
            "optimized_g3_rank",
            "optimized_g4_rank",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, record in enumerate(records):
            writer.writerow(
                {
                    "question_id": record["question_id"],
                    "fold": fold_by_index[index],
                    "expected_image": record["expected_image"],
                    "expected_stage": record["expected_stage"],
                    "predicted_stage": record["classification"]["predicted_stage"],
                    "stage_score": record["classification"]["score"],
                    "stage_margin": record["classification"]["margin"],
                    "legacy_g3_rank": int(g3["legacy_ranks"][index]) or "",
                    "optimized_g3_rank": int(best_g3_ranks[index]) or "",
                    "optimized_g4_rank": int(best_g4_ranks[index]) or "",
                }
            )

    mapping_rows = [row for row in g3["isolated_mapping"] if row["semantic_mode"] == "robust_cosine"]
    mapping_rows.sort(key=lambda row: row["bbox_weight"])
    g3_ci = bootstrap_ci(g3["recommended_ranks"], "mrr")
    g4_ci = bootstrap_ci(g4["recommended_ranks"], "mrr")
    delta_ci = bootstrap_delta_ci(g3["recommended_ranks"], g4["recommended_ranks"], "mrr")
    legacy_delta_ci = bootstrap_delta_ci(g3["legacy_ranks"], g3["recommended_ranks"], "mrr")
    applied = g4["recommended_applied"]
    stage_correct = sum(r["classification"]["predicted_stage"] == r["expected_stage"] for r in records)

    lines = [
        "# 검색 가중치 최적화 결과",
        "",
        "## 실험 원칙",
        "",
        "- SigLIP 이미지와 텍스트 특징은 각각 한 번만 계산하고 이후 실험은 저장된 점수를 재정렬하는 방식으로 수행했다.",
        "- 질문 또는 정답 이미지 파일명을 점수 계산 입력으로 사용하지 않았다. 정답 이미지는 검색 순위 평가에만 사용했다.",
        "- 70개 질의를 5개 fold로 나누고, 각 fold를 제외한 질문에서 가중치를 선택한 뒤 제외한 fold에서 평가했다.",
        "- 최적화 우선순위는 Image MRR, Image Recall@5, Image Recall@1, Image Recall@10 순서로 고정했다.",
        "- 최종 배포용 값은 5-fold 검증 후 70개 전체에서 다시 선택한 탐색적 설정이다. 별도 외부 test set이 없으므로 확증적 최종 성능으로 과도하게 해석하면 안 된다.",
        "",
        "## 기존 설정 재현과 교차검증 결과",
        "",
        "| 구성 | Image R@1 | Image R@5 | Image R@10 | Image MRR |",
        "|---|---:|---:|---:|---:|",
        metric_table_row("기존 G3 재구성", g3["legacy_metrics"]),
        metric_table_row("G3 비제약 탐색 5-fold", g3["selection"]["cv_metrics"]),
        metric_table_row("G3 제약 탐색 5-fold", g3["constrained_selection"]["cv_metrics"]),
        metric_table_row("G3 권장 반올림 설정(70개 탐색)", g3["recommended_metrics"]),
        metric_table_row("기존 G4 재구성", g4["legacy_current_metrics"]),
        metric_table_row("G4 고정 분류 임계값 5-fold", g4["fixed_threshold_selection"]["cv_metrics"]),
        metric_table_row("G4 권장 반올림 설정(70개 탐색)", g4["recommended_metrics"]),
        "",
        f"- G3 권장 설정 Image MRR 95% bootstrap CI: {g3_ci[0]:.3f} - {g3_ci[1]:.3f}",
        f"- G4 권장 설정 Image MRR 95% bootstrap CI: {g4_ci[0]:.3f} - {g4_ci[1]:.3f}",
        f"- 권장 G3-기존 G3 Image MRR 차이 95% bootstrap CI: {legacy_delta_ci[0]:+.3f} - {legacy_delta_ci[1]:+.3f}",
        f"- 권장 G4-권장 G3 Image MRR 차이 95% bootstrap CI: {delta_ci[0]:+.3f} - {delta_ci[1]:+.3f}",
        "",
        "## BBox와 SigLIP 비율 비교",
        "",
        "후보 수에 영향을 받지 않는 robust cosine 점수를 사용했다. 아래 표는 G3 나머지 가중치를 기존값으로 고정한 민감도 분석이다.",
        "",
        "| BBox | SigLIP | Image R@1 | Image R@5 | Image R@10 | Image MRR |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in mapping_rows:
        metric = row["metrics"]
        lines.append(
            f"| {row['bbox_weight']:.1f} | {row['siglip_weight']:.1f} | {percent(metric['r1'])} | "
            f"{percent(metric['r5'])} | {percent(metric['r10'])} | {metric['mrr']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## 선택된 G3 설정",
            "",
            f"- SigLIP 점수: `{g3_best['semantic_mode']}`",
            f"- BBox : SigLIP = {g3_best['bbox_weight']:.1f} : {g3_best['siglip_weight']:.1f}",
            "- BBox는 가중합 순위 점수보다 300-point 공간 후보 필터와 인접 페이지 제한에 사용한다.",
            f"- image search / text rank / page / mapping / diagram = "
            + " / ".join(f"{value:.3f}" for value in g3_best["weights"]),
            f"- source coefficient = {g3_best['source_coefficient']:.3f}",
            "",
            "## G3 ablation",
            "",
            "| 구성 | Image R@1 | Image R@5 | Image R@10 | Image MRR |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in g3_ablation:
        lines.append(metric_table_row(row["label"], row["metrics"]))

    lines.extend(
        [
            "",
            "## 선택된 G4 설정",
            "",
            f"- 단계 적용 최소 score / margin = {g4_best['min_score']:.2f} / {g4_best['min_margin']:.2f}",
            f"- page / keyword / section = " + " / ".join(f"{value:.3f}" for value in g4_best["map_weights"]),
            f"- stage query scale / stage rank scale = {g4_best['query_scale']:.2f} / {g4_best['rank_scale']:.2f}",
            f"- context coefficient / page prior coefficient = {g4_best['context_coefficient']:.2f} / {g4_best['page_prior_coefficient']:.2f}",
            f"- base rank window = {g4_best['rank_window']}",
            f"- 자동 단계 Top-1 정확도 = {stage_correct}/{len(records)} ({percent(stage_correct / len(records))})",
            f"- 권장 임계값 적용 질문 = {int(applied.sum())}/{len(records)} ({percent(float(applied.mean()))})",
            "",
            "## G4 ablation",
            "",
            "| 구성 | Image R@1 | Image R@5 | Image R@10 | Image MRR |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in g4_ablation:
        lines.append(metric_table_row(row["label"], row["metrics"]))

    lines.extend(
        [
            "",
            "## 텍스트 G4 가중치",
            "",
            "텍스트 재정렬은 탐색값이 전체 70개에서는 소폭 높았지만 5-fold 검증에서 일관된 개선이 확인되지 않아 기존 설정을 유지한다.",
            "",
            f"- page / keyword / section = " + " / ".join(f"{value:.3f}" for value in text_best["map_weights"]),
            f"- stage coefficient = {text_best['stage_coefficient']:.2f}",
            "",
            "| 구성 | Text R@1 | Text R@5 | Text R@10 | Text MRR |",
            "|---|---:|---:|---:|---:|",
            metric_table_row("현재 텍스트 G4", text_g4["current_metrics"]),
            metric_table_row("텍스트 G4 5-fold 검증", text_g4["selection"]["cv_metrics"]),
            metric_table_row("텍스트 G4 전체 재선택", text_g4["selection"]["global_metrics"]),
            "",
            "## 해석 제한",
            "",
            "- 동일한 70개 질문 안에서 교차검증했으므로, 선택된 가중치를 논문의 확정값으로 사용하기 전 별도 외부 질문 세트 검증이 권장된다.",
            "- 응답 생성 품질은 이번 탐색 대상이 아니다. 검색 가중치가 확정된 뒤 최종 설정에서만 LLM 응답을 다시 생성해야 한다.",
            "- 가중치가 0에 가깝거나 제거했을 때 성능이 유지되는 구성요소는 단순화 후보이며, 무조건 시스템에서 삭제하기 전에 fold별 일관성을 확인해야 한다.",
            "",
            "## 산출 파일",
            "",
            f"- `{BEST_CONFIG_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- `{G3_SEARCH_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- `{G4_SEARCH_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
            f"- `{QUESTION_RANKS_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pair_cache, feature_cache = load_caches()
    records = feature_cache["records"]
    folds = make_folds(records)
    print("Fold sizes:", [len(fold) for fold in folds], flush=True)

    g3 = g3_search(feature_cache, pair_cache, folds)
    print("G3 CV:", g3["selection"]["cv_metrics"], flush=True)
    print("G3 all-data best:", g3["selection"]["global_metrics"], flush=True)

    g4 = g4_search(feature_cache, g3, folds)
    print("G4 CV:", g4["selection"]["cv_metrics"], flush=True)
    print("G4 all-data best:", g4["selection"]["global_metrics"], flush=True)

    text_g4 = text_g4_search(feature_cache, g4, folds)
    g3_ablation = g3_ablations(g3, feature_cache, pair_cache)
    g4_ablation = g4_ablations(g4)
    write_outputs(feature_cache, pair_cache, folds, g3, g4, text_g4, g3_ablation, g4_ablation)
    print(f"Created: {REPORT_PATH}")
    print(f"Created: {BEST_CONFIG_PATH}")


if __name__ == "__main__":
    main()
