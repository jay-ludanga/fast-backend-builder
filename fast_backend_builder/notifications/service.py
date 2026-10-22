import pickle
import threading
from typing import Any, Dict

from bullmq import Queue

from fast_backend_builder.auth.redis import RedisClient
from fast_backend_builder.models.notification import FailedTask
from fast_backend_builder.utils.error_logging import log_exception


class NotificationService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(NotificationService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.redis = None
            self.redis_url = None
            self.redis_conn = None
            self.queue = None
            self.initialized = False

    @classmethod
    def get_instance(cls):
        """Get the initialized instance of NotificationService."""
        if cls._instance is None or not cls._instance.initialized:
            raise Exception("Notification service is not initialized.")
        return cls._instance

    async def init(self, redis_host: str, redis_password: str, redis_port: int = 6379, debug: bool = True):
        """Initialize the Notification service asynchronously with the given configuration."""
        try:
            if not self.initialized:
                if debug:
                    self.redis_url = f"redis://{redis_host}:{redis_port}"
                    self.redis_conn = {
                        'host': redis_host,
                        'port': redis_port
                    }
                else:
                    self.redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}"
                    self.redis_conn = {
                        'host': redis_host,
                        'port': redis_port,
                        'password': redis_password,
                    }
                self.redis = RedisClient(host=redis_host, port=redis_port, password=redis_password, debug=debug)

                self.initialized = True
                print(f"Notification Service initialized")
            else:
                print("Notification Service is already initialized.")
            return True
        except Exception as e:
            log_exception(e)
            return False

    async def put_message_on_queue(
            self,
            queue: str,
            message: dict,
            job_name: str = None,
            opts: Dict[str, Any] = None,
            job_id: str = None,
    ):
        """Add a single job, optionally using a custom job ID."""

        if not self.initialized:
            raise Exception("Notification service is not initialized.")

        queue_obj = None
        name = job_name or message.get("job_name")

        try:
            if not name:
                raise ValueError("Job name is required.")

            queue_obj = Queue(
                queue,
                {"connection": self.redis_conn},
            )

            options = dict(opts or {})

            # Use custom ID only when supplied explicitly.
            if job_id:
                options["jobId"] = job_id

            job = await queue_obj.add(name, message, options)

            print(f"Notification job submitted with ID {job.id}")
            return job

        except Exception as e:
            log_exception(e)

            await FailedTask.create(
                name=name or "unknown",
                func=(
                    "notifications.NotificationService"
                    ".get_instance().put_message_on_queue"
                ),
                args=pickle.dumps({
                    "queue": queue,
                    "job_name": name,
                    "message": message,
                    "opts": opts,
                    "job_id": job_id,
                }),
                result=str(e),
            )
            return None

        finally:
            if queue_obj is not None:
                await queue_obj.close()

    async def put_bulk_messages_on_queue(
            self,
            queue_name: str,
            messages: list[dict],
            job_name_field: str = "job_name",
    ):
        """Add multiple jobs, supporting an optional custom ID per message.

        Supply job_id at the top level of each message.
        """

        if not self.initialized:
            raise Exception("Notification service is not initialized.")

        queue = None

        try:
            queue = Queue(
                queue_name,
                {"connection": self.redis_conn},
            )

            jobs_bulk = []

            for msg in messages:
                options = dict(msg.get("opts") or {})
                job_id = msg.get("job_id")

                if job_id:
                    options["jobId"] = job_id

                jobs_bulk.append({
                    "name": msg.get(job_name_field, "default_job"),
                    "data": msg,
                    "opts": options,
                })

            result = await queue.addBulk(jobs_bulk)

            print(
                f"Submitted {len(result)} jobs to {queue_name}"
            )
            return result

        except Exception as e:
            log_exception(e)

            for msg in messages:
                await FailedTask.create(
                    name=msg.get(job_name_field, "default_job"),
                    func=(
                        "notifications.NotificationService"
                        ".put_bulk_messages_on_queue"
                    ),
                    args=pickle.dumps({
                        "queue": queue_name,
                        "message": msg,
                    }),
                    result=str(e),
                )

            return []

        finally:
            if queue is not None:
                await queue.close()


notification_service = NotificationService()
