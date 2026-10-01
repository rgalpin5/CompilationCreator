"""How many tasks to run at once on this computer.

Download and encode pools used to be fixed numbers. Those numbers are still the
ceiling on a small machine. A larger machine may prepare more clips at once,
and a smaller one opens fewer connections. The files each task writes do not
change.
"""

from __future__ import annotations

import os


def available_cpus() -> int:
    """CPUs this process may use.

    ``sched_getaffinity`` exists on Unix and reports a container limit.
    Windows uses ``os.cpu_count`` instead.
    """
    affinity = getattr(os, "sched_getaffinity", None)
    if affinity is not None:
        try:
            allowed = len(affinity(0))
        except OSError:
            allowed = 0
        if allowed > 0:
            return allowed
    count = os.cpu_count()
    if count is None or count < 1:
        return 1
    return count


def download_workers(task_count: int) -> int:
    """Parallel clip downloads. They wait on the network, so the ceiling stays at 4."""
    if task_count < 1:
        return 1
    return max(1, min(4, available_cpus(), task_count))


def prepare_workers(task_count: int, *, encodes_video: bool) -> int:
    """Parallel clip preparation.

    Picture encodes use libx264, which already spreads across cores, so the
    pool is one process per two CPUs and never more than eight. Stream copy
    and audio remux stay at the previous ceiling of four. A one- or two-core
    machine runs a single picture encode.
    """
    if task_count < 1:
        return 1
    cpus = available_cpus()
    per_core = max(1, min(8, cpus // 2 or 1))
    ceiling = per_core if encodes_video else max(1, min(4, cpus))
    return max(1, min(ceiling, task_count))


def fragment_connections() -> int:
    """yt-dlp fragment connections for one full-file download.

    An 8-core machine still opens 16, which was the previous fixed value.
    Smaller machines open fewer sockets. The cap stays 16.
    """
    return max(4, min(16, available_cpus() * 2))
