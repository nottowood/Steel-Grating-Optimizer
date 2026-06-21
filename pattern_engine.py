"""Pattern Engine for Steel Grating Optimizer.

Generates all valid cross-bar patterns for a given cut length and product type,
then selects the best pattern based on manufacturing priority rules.

Selection Priority:
  P1: Start Length in preferred range 40-45 mm
  P2: If no preferred exists → smallest valid Start Length (closest to 15 mm)
  P3: Maximum Rod Qty (more cross bars = stronger panel)
  P4: Minimum waste (smallest start length = least material unused)
"""

from models import Pattern

MINIMUM_START_LENGTH = 15.0
PREFERRED_START_MIN = 40.0
PREFERRED_START_MAX = 45.0


def generate_patterns(cut_length: float, cross_bar_pitch: float) -> list[Pattern]:
    """Generate all valid cross-bar patterns for a given cut length.

    A pattern is valid when:
    - rod_qty >= 2 (at least 2 cross bars)
    - start_length >= 15 mm
    - start_length == end_length (symmetric)

    Patterns are returned sorted by rod_qty descending (most rods first).
    """
    patterns = []
    rod_qty = 2
    while True:
        mid_length = (rod_qty - 1) * cross_bar_pitch
        remaining = cut_length - mid_length
        if remaining < 2 * MINIMUM_START_LENGTH:
            break
        start_length = remaining / 2.0
        if start_length >= MINIMUM_START_LENGTH:
            pattern = Pattern(
                rod_qty=rod_qty,
                mid_length=round(mid_length, 2),
                start_length=round(start_length, 2),
                end_length=round(start_length, 2),
            )
            patterns.append(pattern)
        rod_qty += 1

    patterns.sort(key=lambda p: p.rod_qty, reverse=True)
    _rank_patterns(patterns)
    return patterns


def _rank_patterns(patterns: list[Pattern]) -> None:
    """Assign rank and score to each pattern based on selection priority.

    Sort key (all ascending = better):
      tier: 0 = preferred range, 1 = outside range
      start_length: smaller is better (P2 + P4)
      -rod_qty: more rods is better (P3, negated for ascending sort)
    """
    if not patterns:
        return

    def sort_key(p: Pattern) -> tuple:
        tier = 0 if p.is_preferred else 1
        return (tier, p.start_length, -p.rod_qty)

    ranked = sorted(patterns, key=sort_key)

    for rank_idx, pat in enumerate(ranked, start=1):
        pat.rank = rank_idx
        pat.score = len(patterns) - rank_idx + 1

    for pat in patterns:
        if pat.rank == 1:
            if pat.is_preferred:
                pat.selection_reason = f"P1: Start {pat.start_length} mm อยู่ในช่วง 40-45 mm"
            else:
                pat.selection_reason = (
                    f"P2: ไม่มี pattern ในช่วง 40-45 mm → "
                    f"เลือก Start น้อยสุด {pat.start_length} mm "
                    f"(Rod={pat.rod_qty}, waste น้อยสุด)"
                )


def select_best_pattern(
    patterns: list[Pattern], floor_pattern_rod_qty: int | None = None
) -> Pattern | None:
    """Select the best pattern (rank=1) from a list of ranked patterns.

    If floor_pattern_rod_qty is specified and a preferred pattern matches,
    it gets priority for visual consistency.
    """
    if not patterns:
        return None

    if floor_pattern_rod_qty is not None:
        floor_preferred = [
            p for p in patterns
            if p.rod_qty == floor_pattern_rod_qty and p.is_preferred
        ]
        if floor_preferred:
            best = floor_preferred[0]
            best.selection_reason = (
                f"P1+Floor: Start {best.start_length} mm ในช่วง 40-45 mm "
                f"และตรงกับ Floor Pattern (Rod={floor_pattern_rod_qty})"
            )
            return best

    return min(patterns, key=lambda p: p.rank)
