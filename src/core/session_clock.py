import math
import time

from datetime import datetime, timezone
from threading import Lock


class SessionClock:
    """
    Единая временная шкала одной лекции.

    monotonic используется для измерения длительности
    и синхронизации аудио с экраном.

    UTC используется для календарных временных меток.
    """

    def __init__(self):
        self._lock = Lock()

        self._started = False
        self._monotonic_start = None
        self._utc_start = None

    @property
    def is_started(self):
        return self._started

    def start(self):
        """Начинает отсчёт новой сессии."""
        with self._lock:
            self._utc_start = time.time()
            self._monotonic_start = time.monotonic()
            self._started = True

    def restore(self, started_at_utc):
        """
        Восстанавливает временную шкалу после перезапуска приложения.

        started_at_utc — исходное время начала лекции в ISO 8601.
        """
        if not isinstance(started_at_utc, str):
            raise TypeError(
                "started_at_utc должен быть строкой ISO 8601"
            )

        try:
            started_at = datetime.fromisoformat(
                started_at_utc.replace("Z", "+00:00")
            )
        except ValueError as error:
            raise ValueError(
                "Некорректное время начала сессии"
            ) from error

        if started_at.tzinfo is None:
            raise ValueError(
                "Время начала должно содержать часовой пояс"
            )

        utc_start = started_at.astimezone(
            timezone.utc
        ).timestamp()

        utc_now = time.time()
        elapsed_seconds = utc_now - utc_start

        if elapsed_seconds < 0:
            raise ValueError(
                "Время начала сессии находится в будущем"
            )

        monotonic_now = time.monotonic()

        with self._lock:
            self._utc_start = utc_start
            self._monotonic_start = (
                monotonic_now - elapsed_seconds
            )
            self._started = True

    def _ensure_started(self):
        if not self._started:
            raise RuntimeError(
                "SessionClock ещё не запущен"
            )

    def elapsed(self, monotonic_at=None):
        """
        Возвращает время события в секундах
        относительно начала сессии.
        """
        self._ensure_started()

        if monotonic_at is None:
            monotonic_at = time.monotonic()

        monotonic_at = float(monotonic_at)

        if not math.isfinite(monotonic_at):
            raise ValueError(
                "Некорректная монотонная временная метка"
            )

        return monotonic_at - self._monotonic_start

    def to_utc_iso(self, monotonic_at):
        """
        Преобразует монотонную метку события
        в UTC ISO 8601.
        """
        self._ensure_started()

        elapsed_seconds = self.elapsed(monotonic_at)

        timestamp = (
            self._utc_start + elapsed_seconds
        )

        return datetime.fromtimestamp(
            timestamp,
            timezone.utc
        ).isoformat()

    def now(self):
        """Возвращает временные данные текущего момента."""
        monotonic_at = time.monotonic()

        return {
            "monotonic_at": monotonic_at,
            "elapsed_seconds": self.elapsed(monotonic_at),
            "utc": self.to_utc_iso(monotonic_at),
        }