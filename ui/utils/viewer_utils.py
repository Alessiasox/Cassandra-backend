from datetime import datetime, timedelta
from typing import Dict, List, Optional


def generate_timeline(
    start_dt: datetime, end_dt: datetime, step_minutes: int
) -> List[datetime]:
    """
    Return a list of datetimes from start_dt to end_dt inclusive,
    stepping by `step_minutes`. If end_dt < start_dt, returns [].
    """
    if end_dt < start_dt or step_minutes <= 0:
        return []
    total_secs = (end_dt - start_dt).total_seconds()
    count = int(total_secs // (step_minutes * 60)) + 1
    return [start_dt + timedelta(minutes=step_minutes * i) for i in range(count)]


def closest_match(images: List[Dict], target_dt: datetime) -> Optional[Dict]:
    """
    Given a list of dicts each with a 'timestamp' key (a datetime),
    return the dict whose timestamp is nearest to target_dt.
    Returns None if images is empty.
    """
    if not images:
        return None
    return min(images, key=lambda img: abs(img["timestamp"] - target_dt)) 