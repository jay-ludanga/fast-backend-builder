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

    async def put_message_on_queue(self, queue: str, message: dict, job_name: str = None, opts: Dict[str, Any] = None):
        """
            This will put the message to be sent later on a Queue
        :return:
        """
        if self.initialized:
            try:
                self.queue = Queue(queue, {
                    'connection': self.redis_conn
                })
                if opts:
                    job = await self.queue.add(
                        job_name if job_name else message.get('job_name'),
                        message,
                        opts
                    )
                else:
                    job = await self.queue.add(
                        job_name if job_name else message.get('job_name'),
                        message
                    )
                print(f"Notification job Added successfully with ID {job.id}")
                await self.queue.close()
            except Exception as e:
                log_exception(e)
                # Create FailedTask instance first
                failed = await FailedTask.create(
                    name=f"{job_name if job_name else message.get('job_name')}",
                    func='notifications.NotificationService.get_instance().put_message_on_queue',
                    args=pickle.dumps({'queue': queue, 'job_name': job_name if job_name else message.get('job_name'), 'message': message}),
                    result=str(e)
                )

                # Set the args using your serialization method
                # await failed.set_args({'message': message})
        else:
            raise Exception("Notification service is not initialized.")


    async def put_bulk_messages_on_queue(
            self,
            queue_name: str,
            messages: list[dict],
            job_name_field: str = "job_name",
    ):
        """
        Adds multiple jobs to the queue efficiently using addBulk
        """
        if not self.initialized:
            raise Exception("Notification service is not initialized.")

        try:
            queue = Queue(queue_name, {"connection": self.redis_conn})

            # Prepare bulk jobs
            jobs_bulk = [
                {
                    "name": msg.get(job_name_field, "default_job"),
                    "data": msg,
                    "opts": msg.get("opts", {})
                }
                for msg in messages
            ]

            # Add all jobs at once
            result = await queue.addBulk(jobs_bulk)
            print(f"Added {len(result)} jobs to {queue_name} successfully")
            await queue.close()
            return result
        except Exception as e:
            log_exception(e)
            # optionally log FailedTask for each message
            for msg in messages:
                await FailedTask.create(
                    name=msg.get(job_name_field, "default_job"),
                    func="notifications.NotificationService.put_bulk_messages_on_queue",
                    args=pickle.dumps({"queue": queue_name, "message": msg}),
                    result=str(e)
                )
            return []


notification_service = NotificationService()
