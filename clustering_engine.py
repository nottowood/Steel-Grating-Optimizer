"""Start Clustering Engine for Phase-2 optimization.

Groups similar Start Lengths into clusters of visual compatibility.
Panels with Start Lengths in the same cluster are considered
visually consistent when installed on the same floor.

Cluster width is fixed at 10 mm (±5 mm from center).
"""

from optimizer_models import StartCluster

CLUSTER_HALF_WIDTH = 5.0


def build_clusters(all_starts: list[float]) -> list[StartCluster]:
    """Build clusters from a list of all unique Start Lengths.

    Each unique start becomes a cluster center.
    Cluster range = center ± 5 mm.
    Overlapping clusters are merged.
    """
    if not all_starts:
        return []

    unique = sorted(set(all_starts))

    raw_clusters = []
    for s in unique:
        raw_clusters.append((s - CLUSTER_HALF_WIDTH, s + CLUSTER_HALF_WIDTH, [s]))

    merged = [raw_clusters[0]]
    for low, high, members in raw_clusters[1:]:
        prev_low, prev_high, prev_members = merged[-1]
        if low <= prev_high:
            merged[-1] = (prev_low, max(prev_high, high), prev_members + members)
        else:
            merged.append((low, high, members))

    clusters = []
    for i, (low, high, members) in enumerate(merged):
        center = sum(members) / len(members)
        clusters.append(StartCluster(
            cluster_id=i + 1,
            center=round(center, 2),
            low=round(low, 2),
            high=round(high, 2),
            member_starts=members,
        ))
    return clusters


def find_cluster_for_start(start: float, clusters: list[StartCluster]) -> StartCluster | None:
    """Find which cluster a given Start Length belongs to."""
    for cluster in clusters:
        if cluster.contains(start):
            return cluster
    return None


def get_panel_clusters(
    panel_patterns: dict[str, list[float]],
    clusters: list[StartCluster],
) -> dict[int, dict]:
    """For each cluster, determine which panels have at least one pattern in it.

    Args:
        panel_patterns: {mark: [start_length, ...]}
        clusters: list of StartCluster

    Returns:
        {cluster_id: {"cluster": StartCluster, "matching": {mark: best_start}, "non_matching": [mark]}}
    """
    all_marks = list(panel_patterns.keys())
    result = {}

    for cluster in clusters:
        matching = {}
        non_matching = []
        for mark in all_marks:
            starts = panel_patterns[mark]
            candidates_in_cluster = [s for s in starts if cluster.contains(s)]
            if candidates_in_cluster:
                matching[mark] = _pick_best_in_cluster(candidates_in_cluster, cluster)
            else:
                non_matching.append(mark)
        result[cluster.cluster_id] = {
            "cluster": cluster,
            "matching": matching,
            "non_matching": non_matching,
        }
    return result


def _pick_best_in_cluster(starts: list[float], cluster: StartCluster) -> float:
    """Pick the best start length within a cluster.

    Prefer values in 40-45 mm range, then closest to cluster center.
    """
    preferred = [s for s in starts if 40.0 <= s <= 45.0]
    if preferred:
        return min(preferred, key=lambda s: abs(s - 42.5))
    return min(starts, key=lambda s: abs(s - cluster.center))
