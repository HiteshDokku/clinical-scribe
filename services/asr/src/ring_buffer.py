import collections
import threading

class RingBuffer:
    def __init__(self, maxlen: int):
        self._buffer = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, data: bytes):
        with self._lock:
            self._buffer.append(data)

    def drain(self) -> bytes:
        with self._lock:
            data = b"".join(self._buffer)
            self._buffer.clear()
            return data
    
    def clear(self):
        with self._lock:
            self._buffer.clear()

    def get_all(self) -> bytes:
        with self._lock:
            return b"".join(self._buffer)
