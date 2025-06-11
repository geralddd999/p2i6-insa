import time, logging

class DedupFilter(logging.Filter):
    def __init__(self, period = 30.0):
        super().__init__()
        self.period = period
        self._cache = {}

    def filter(self,record):
        key = (record.name, record.levelno, record.getMessage())
        now = time.time()
        last = self._cache.get(key,0)
        self._cache[key] = now
        return (now - last) >= self.period
