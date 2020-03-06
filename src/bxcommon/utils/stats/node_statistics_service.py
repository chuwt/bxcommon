import gc
from collections import defaultdict
from typing import Dict

from bxcommon import constants
from bxcommon.utils.stats.statistics_service import StatsIntervalData, StatisticsService
from bxutils import logging
from bxutils.logging import LogRecordType


class NodeTransactionStatInterval(StatsIntervalData):
    total_uncollectable: int
    generation_zero_size: int
    generation_one_size: int
    generation_two_size: int
    time_spent_in_gc: int
    collection_counts: Dict[int, int]


    def __init__(self, *args, **kwargs):
        super(NodeTransactionStatInterval, self).__init__(*args, **kwargs)
        self.total_uncollectable = 0
        self.generation_zero_size = 0
        self.generation_one_size = 0
        self.generation_two_size = 0
        self.collection_counts = defaultdict(int)
        self.generation_zero_collections = 0
        self.generation_one_collections = 0
        self.generation_two_collections = 0
        self.time_spent_in_gc = 0


class _NodeStatisticsService(StatisticsService):
    INTERVAL_DATA_CLASS = NodeTransactionStatInterval

    def __init__(self, interval=constants.NODE_STATS_INTERVAL_S):
        super().__init__(
            "NodeStatus",
            interval,
            reset=True,
            logger=logging.get_logger(LogRecordType.NodeStatus, __name__),
        )

    def log_gc_duration(self, generation: int, duration_s: int):
        self.interval_data.time_spent_in_gc += duration_s
        self.interval_data.collection_counts[generation] += 1

    def get_info(self):
        gen0, gen1, gen2 = gc.get_count()
        return {
            "garbage_collection": {
                "uncollectable": len(gc.garbage),
                "collection_counts": {
                    f"gen{k}": v for k, v in self.interval_data.collection_counts
                },
                "sizes": {
                    "gen0": gen0,
                    "gen1": gen1,
                    "gen2": gen2,
                },
                "total_elapsed_time": self.interval_data.time_spent_in_gc,
            }
        }


node_stats_service = _NodeStatisticsService()
