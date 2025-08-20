import threading
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.strawberry import StrawberryIntegration
from sentry_sdk.integrations.celery import CeleryIntegration


class SentryService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SentryService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = False

    @classmethod
    def get_instance(cls):
        """Get the initialized instance of SentryService."""
        if cls._instance is None or not cls._instance.initialized:
            raise Exception("Sentry service is not initialized.")
        return cls._instance

    def init(self, dsn: str, traces_sample_rate: float = 1.0, failed_request_status_codes=None, debug: bool = False):
        """Initialize the Sentry service with the given configuration."""
        if failed_request_status_codes is None:
            failed_request_status_codes = {403, *range(500, 599)}

        if not self.initialized:
            sentry_sdk.init(
                dsn=dsn,
                debug=debug,  # Enable or disable debug mode
                integrations=[
                    FastApiIntegration(
                        transaction_style="endpoint",
                        failed_request_status_codes=failed_request_status_codes,
                    ),
                    StrawberryIntegration(async_execution=True),
                    CeleryIntegration(monitor_beat_tasks=True)
                ],
                traces_sample_rate=traces_sample_rate,
            )
            self.initialized = True
            print("Sentry initialized successfully.")
        else:
            print("Sentry service is already initialized.")

    def capture_exception(self, exception: Exception):
        """Capture an exception and send it to Sentry."""
        if not self.initialized:
            raise Exception("Sentry service is not initialized. Please initialize before capturing exceptions.")
        sentry_sdk.capture_exception(exception)

    def capture_message(self, message: str, level: str = "info"):
        """Capture a custom message in Sentry with the specified level."""
        if not self.initialized:
            raise Exception("Sentry service is not initialized. Please initialize before capturing messages.")
        sentry_sdk.capture_message(message, level=level)
