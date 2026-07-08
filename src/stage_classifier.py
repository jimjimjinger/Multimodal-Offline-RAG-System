import math

from rag_search import load_stage_context_map


DEFAULT_STAGE_TOP_K = 3
DEFAULT_STAGE_MIN_SCORE = 0.45
DEFAULT_STAGE_MIN_MARGIN = 0.03


def _text(value):
    return str(value or "").strip()


def _join_terms(values):
    terms = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            terms.extend(_text(item) for item in value if _text(item))
        elif _text(value):
            terms.append(_text(value))
    return " ".join(terms)


def build_stage_profiles(map_path):
    context_map = load_stage_context_map(str(map_path))
    profiles = []
    for stage, context in sorted(context_map.items()):
        text = _join_terms(
            [
                context.get("stage_id"),
                context.get("stage"),
                context.get("section_terms", []),
                context.get("content_terms", []),
                context.get("action_terms", []),
                context.get("evidence"),
            ]
        )
        profiles.append(
            {
                "stage": stage,
                "stage_id": context.get("stage_id", ""),
                "profile_text": text,
                "context": context,
            }
        )
    return profiles


def encode_stage_profiles(embedder, profiles):
    if not profiles:
        return []
    texts = [profile["profile_text"] for profile in profiles]
    return embedder.encode(texts)


def cosine_similarity(vec_a, vec_b):
    numerator = sum(float(a) * float(b) for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(float(a) * float(a) for a in vec_a))
    norm_b = math.sqrt(sum(float(b) * float(b) for b in vec_b))
    if not norm_a or not norm_b:
        return 0.0
    return numerator / (norm_a * norm_b)


def classify_stage(
    question,
    embedder,
    profiles,
    profile_embeddings,
    top_k=DEFAULT_STAGE_TOP_K,
    min_score=DEFAULT_STAGE_MIN_SCORE,
    min_margin=DEFAULT_STAGE_MIN_MARGIN,
):
    if not _text(question) or not profiles or len(profiles) != len(profile_embeddings):
        return {
            "stage_label": None,
            "predicted_stage": "",
            "score": 0.0,
            "margin": 0.0,
            "used": False,
            "top_candidates": [],
            "reason": "stage profile not available",
        }

    question_embedding = embedder.encode(question)
    candidates = []
    for profile, profile_embedding in zip(profiles, profile_embeddings):
        score = cosine_similarity(question_embedding, profile_embedding)
        candidates.append(
            {
                "stage": profile["stage"],
                "stage_id": profile["stage_id"],
                "score": round(score, 4),
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    top_candidates = candidates[: max(1, top_k)]
    best = top_candidates[0]
    second_score = top_candidates[1]["score"] if len(top_candidates) > 1 else 0.0
    margin = round(best["score"] - second_score, 4)
    used = best["score"] >= min_score and margin >= min_margin
    return {
        "stage_label": best["stage"] if used else None,
        "predicted_stage": best["stage"],
        "score": best["score"],
        "margin": margin,
        "used": used,
        "top_candidates": top_candidates,
        "reason": "score and margin above threshold" if used else "score or margin below threshold",
    }
