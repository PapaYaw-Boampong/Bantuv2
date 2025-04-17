import uuid
from typing import Dict, List, Optional, Tuple, Any

from datetime import datetime, timedelta
import random

import json

from models import (

    EvaluationBranch,
    EvaluationStep,

)


def create_pairings(contribution_ids: List[str]) -> Tuple[str, List[Tuple[str, str]]]:
    random.shuffle(contribution_ids)
    pairs = []

    for i in range(0, len(contribution_ids), 2):
        if i + 1 < len(contribution_ids):
            pairs.append((contribution_ids[i], contribution_ids[i + 1]))

    if len(contribution_ids) % 2 != 0:
        pairs.append((contribution_ids[-1], contribution_ids[0]))  # loop last with first

    return str(uuid.uuid4()), pairs


def filter_user_participated(branches: List[EvaluationBranch], user_id: uuid.UUID) -> List[EvaluationBranch]:
    filtered = []
    for branch in branches:
        instance = branch.evaluation_instance
        has_participated = any(
            step.user_id == user_id
            for b in instance.evaluation_branches
            for step in b.evaluation_steps
        )
        if not has_participated:
            filtered.append(branch)
    return filtered


def prioritize_branches(
        branches: List[EvaluationBranch],
        proficiency: int,
        threshold: float = 0.4
) -> List[EvaluationBranch]:
    def relative_depth(b: EvaluationBranch):
        return len(b.evaluation_steps) / (b.max_depth or 1)

    reverse = proficiency >= 7
    sorted_branches = sorted(branches, key=relative_depth, reverse=reverse)

    if proficiency < 7:
        shallow_enough = [b for b in sorted_branches if relative_depth(b) <= threshold]
        return shallow_enough

    return sorted_branches


def is_expired(step: EvaluationStep) -> bool:
    if not step.assigned_at:
        return True
    expiration = step.assigned_at + timedelta(minutes=15)  # TTL window
    return datetime.utcnow() > expiration


def create_pairs(contribution_ids: List[str]) -> List[Tuple[str, str]]:
    """
    Given a list of contribution IDs, shuffle and pair them for A/B testing.
    If there's an odd one out, it is dropped or can be handled separately.
    """
    # Shuffle to randomize pairings
    shuffled = contribution_ids.copy()
    random.shuffle(shuffled)

    pairs: List[Tuple[str, str]] = []
    for i in range(0, len(shuffled) - 1, 2):
        pairs.append((shuffled[i], shuffled[i + 1]))
    return pairs


def create_stage(pairs: List[Tuple[str, str]]) -> Dict[str, Any]:
    """
    Create a new A/B test stage data structure.

    Structure:
    {
        "stage_id": <uuid>,
        "pairs": [ [id1, id2], ... ],
        "results": { "id1_id2": { user_id: selected_id_or_equal, ... } },
        "complete": False
    }
    """
    return {
        "stage_id": str(uuid.uuid4()),
        "pairs": pairs,
        "results": {},
        "complete": False
    }


def get_active_stage(ab_test_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Retrieve the first not-yet-complete stage from the A/B test data.
    """
    for stage in ab_test_data.get("stages", []):
        if not stage.get("complete", False):
            return stage
    return None


def tally_pair_votes(pair_results: Dict[str, str]) -> List[str]:
    """
    Tally votes for a single pair. Votes can be:
      - A contribution ID
      - The string "equal"

    Returns:
      - Both IDs if "equal" votes reach the majority threshold.
      - Otherwise the ID with the highest count.
    """
    counts: Dict[str, int] = {}
    for vote in pair_results.values():
        counts[vote] = counts.get(vote, 0) + 1

    total_votes = sum(counts.values())
    # Majority threshold: more than half
    threshold = (total_votes // 2) + 1

    equal_count = counts.get("equal", 0)
    # If equal is a majority, advance both
    if equal_count >= threshold:
        # Collect all contribution IDs (keys except "equal")
        return [c for c in counts.keys() if c != "equal"]

    # Otherwise, find the non-equal with max votes
    winner: Optional[str] = None
    max_votes = 0
    for candidate, cnt in counts.items():
        if candidate == "equal":
            continue
        if cnt > max_votes:
            max_votes = cnt
            winner = candidate

    return [winner] if winner else []
