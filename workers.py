import threading
import time

from logger import log


class WorkerManager:
    def __init__(self):
        self._workers = {}
        self._lock = threading.Lock()

    def start(self, name, target):
        with self._lock:
            existing = self._workers.get(name)

            if existing and existing["thread"].is_alive():
                return False

            stop_event = threading.Event()

            def run():
                log(f"{name}: started")
                try:
                    target(stop_event)
                except Exception as exc:
                    log(f"{name}: worker failed: {exc!r}", "error")
                finally:
                    log(f"{name}: stopped")

            thread = threading.Thread(
                target=run,
                name=name,
                daemon=True,
            )

            self._workers[name] = {
                "thread": thread,
                "stop_event": stop_event,
            }
            thread.start()
            return True

    def stop(self, name):
        with self._lock:
            worker = self._workers.get(name)
            if worker is None:
                return

            worker["stop_event"].set()

    def is_running(self, name):
        with self._lock:
            worker = self._workers.get(name)
            return bool(worker and worker["thread"].is_alive())


def ring_worker(stop_event):
    import ring_manager

    while not stop_event.is_set():
        try:
            ring_manager.check_and_equip_ring(force=True)
            time.sleep(1)
        except Exception as exc:
            log(f"Ring manager error: {exc!r}", "error")

        stop_event.wait(0.5)


manager = WorkerManager()