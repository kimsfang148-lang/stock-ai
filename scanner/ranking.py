def rank_candidates(rows, score_key="장기점수", min_long=None):
    """Rank scanner candidates by score, optionally filtering by minimum score."""
    if not rows:
        return []
    result = list(rows)
    if min_long is not None:
        result = [r for r in result if float(r.get(score_key, 0) or 0) >= float(min_long)]
    return sorted(result, key=lambda x: float(x.get(score_key, 0) or 0), reverse=True)
