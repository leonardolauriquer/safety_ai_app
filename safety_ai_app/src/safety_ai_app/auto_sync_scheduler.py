"""
Auto-sync scheduler for the knowledge base.

Runs incremental Google Drive → ChromaDB synchronization in a background
thread at a configurable interval.  The scheduler is a process-level
singleton so only one sync loop ever runs regardless of how many times
Streamlit rerenders the page.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_MINUTES: int = 30
_INITIAL_DELAY_SECONDS: int = 90


class AutoSyncScheduler:
    """Background scheduler that periodically syncs Drive → ChromaDB."""

    def __init__(self, interval_minutes: int = DEFAULT_INTERVAL_MINUTES) -> None:
        self.interval_minutes = interval_minutes
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._wakeup_event = threading.Event()
        self._interval_just_changed: bool = False
        self._lock = threading.Lock()

        self._get_qa: Optional[Callable[[], Any]] = None
        self._get_drive_service: Optional[Callable[[], Any]] = None

        self.last_run_time: Optional[datetime] = None
        self.last_run_success: Optional[bool] = None
        self.last_run_message: str = "Auto-sync ainda não executado."
        self.last_processed_count: int = 0
        self.next_run_time: Optional[datetime] = None
        self.is_syncing: bool = False
        self.enabled: bool = True

    def configure(
        self,
        get_qa: Callable[[], Any],
        get_drive_service: Callable[[], Any],
    ) -> None:
        """Attach factory callables that return the QA and Drive service instances."""
        with self._lock:
            self._get_qa = get_qa
            self._get_drive_service = get_drive_service

    def start(self) -> None:
        """Start the background sync loop (idempotent)."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            # Set next_run_time immediately so the UI can show it from the first render.
            first_run_ts = time.time() + _INITIAL_DELAY_SECONDS
            self.next_run_time = datetime.fromtimestamp(first_run_ts)
            self._thread = threading.Thread(
                target=self._run_loop,
                name="AutoSync_Scheduler",
                daemon=True,
            )
            self._thread.start()
        logger.info(
            "Auto-sync scheduler started (interval: %d min, initial delay: %d s).",
            self.interval_minutes,
            _INITIAL_DELAY_SECONDS,
        )

    def stop(self) -> None:
        """Signal the background loop to stop and wait briefly."""
        self._stop_event.set()
        self._wakeup_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def update_interval(self, new_interval_minutes: int) -> None:
        """Change the sync interval and wake the sleeping loop so it picks up the new value.

        The value is clamped to a safe range (1 – 1440 minutes).  Values outside
        the application's intended option set are accepted but logged as warnings
        so callers are aware of unexpected inputs.
        """
        clamped = max(1, min(int(new_interval_minutes), 1440))
        if clamped != new_interval_minutes:
            logger.warning(
                "Auto-sync interval %r is out of range; clamped to %d min.",
                new_interval_minutes,
                clamped,
            )
        with self._lock:
            self.interval_minutes = clamped
            self._interval_just_changed = True
        self._wakeup_event.set()
        logger.info("Auto-sync interval updated to %d min.", clamped)

    def trigger_now(self) -> bool:
        """
        Trigger an immediate incremental sync in a one-shot background thread.

        Returns False if a sync is already running.
        """
        with self._lock:
            if self.is_syncing:
                return False
        t = threading.Thread(
            target=self._do_sync,
            name="AutoSync_OnDemand",
            daemon=True,
        )
        t.start()
        return True

    def get_status(self) -> dict:
        """Return a snapshot of the scheduler state (safe to call from any thread)."""
        with self._lock:
            return {
                "enabled": self.enabled,
                "interval_minutes": self.interval_minutes,
                "is_syncing": self.is_syncing,
                "last_run_time": self.last_run_time,
                "last_run_success": self.last_run_success,
                "last_run_message": self.last_run_message,
                "last_processed_count": self.last_processed_count,
                "next_run_time": self.next_run_time,
            }

    def _run_loop(self) -> None:
        """Main loop: wait for the initial delay, then sync on every interval."""
        if self._stop_event.wait(timeout=_INITIAL_DELAY_SECONDS):
            return

        while not self._stop_event.is_set():
            if self.enabled:
                self._do_sync()

            # Inner loop: sleep for the configured interval, but restart the
            # timer if the interval is changed while sleeping.
            while not self._stop_event.is_set():
                interval_secs = self.interval_minutes * 60
                next_ts = time.time() + interval_secs
                with self._lock:
                    self.next_run_time = datetime.fromtimestamp(next_ts)
                    self._interval_just_changed = False

                self._wakeup_event.clear()
                self._wakeup_event.wait(timeout=interval_secs)

                if self._stop_event.is_set():
                    return

                with self._lock:
                    changed = self._interval_just_changed

                if changed:
                    # Interval was updated — reset the timer without syncing.
                    continue

                # Normal timeout — break inner loop and run the next sync.
                break

    def _do_sync(self) -> None:
        """Perform one incremental sync cycle."""
        with self._lock:
            if self.is_syncing:
                return
            self.is_syncing = True

        logger.info("Auto-sync: Starting incremental sync...")
        try:
            qa = self._get_qa() if self._get_qa else None
            drive_service = self._get_drive_service() if self._get_drive_service else None

            if not qa or not drive_service:
                logger.warning("Auto-sync: QA or Drive service not available, skipping.")
                with self._lock:
                    self.last_run_time = datetime.now()
                    self.last_run_success = False
                    self.last_run_message = "Serviços não disponíveis (QA ou Drive)."
                return

            from safety_ai_app.google_drive_integrator import (
                synchronize_app_central_library_to_chroma,
            )

            count = synchronize_app_central_library_to_chroma(
                drive_service, qa, progress_callback=None
            )

            with self._lock:
                self.last_run_time = datetime.now()
                self.last_run_success = True
                self.last_processed_count = count
                if count > 0:
                    self.last_run_message = (
                        f"{count} documento(s) novo(s) indexado(s) com sucesso."
                    )
                else:
                    self.last_run_message = "Nenhum documento novo encontrado."

            logger.info("Auto-sync: Completed. %d new document(s) indexed.", count)

        except Exception as exc:
            logger.error("Auto-sync: Error during sync: %s", exc, exc_info=True)
            with self._lock:
                self.last_run_time = datetime.now()
                self.last_run_success = False
                self.last_run_message = f"Erro durante a sincronização: {exc}"
        finally:
            with self._lock:
                self.is_syncing = False


_scheduler: Optional[AutoSyncScheduler] = None
_scheduler_lock = threading.Lock()


def get_scheduler(
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
) -> AutoSyncScheduler:
    """Return the process-level singleton scheduler instance."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None:
            _scheduler = AutoSyncScheduler(interval_minutes=interval_minutes)
        return _scheduler
