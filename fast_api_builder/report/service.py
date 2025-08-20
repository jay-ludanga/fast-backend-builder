from typing import List, Type

from tortoise import Tortoise
from fast_api_builder.common.schemas import ModelType
# from fast_api_builder.muarms.models.report import ReportView
from fast_api_builder.muarms.enums import ReportPriority
from fast_api_builder.notifications.service import NotificationService
from fast_api_builder.utils.error_logging import log_exception
from tortoise.exceptions import ConfigurationError
from tortoise.transactions import in_transaction

from fast_api_builder.utils.metrics.db_metrics import DBMetrics


class ReportService:
    _instance = None
    is_fetching = False

    def __new__(cls, *args, **kwargs):
        # Prevent instantiation if an instance already exists
        if cls._instance is None:
            cls._instance = super(ReportService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # Avoid re-initializing
            """Initialize the service with a default interval."""
            
            self.initialized = True  # Mark as initialized
    
    async def update_report_for(self, models: List[Type[ModelType]], priority: ReportPriority = ReportPriority.LOW):
        try:
            if ReportView.has_dependants(models):
                report_views = ReportView.get_dependants(models)
                
                for report_view in report_views:
                    if priority == ReportPriority.HIGH:
                        await report_view.refresh_view()
                    else:
                        await NotificationService.get_instance().put_message_on_queue(
                            queue="Reports", 
                            message={
                                "refresh_query": report_view.get_refresh_query(),
                                "report_name": report_view.__name__,
                                "priority": priority.value
                            }, 
                            opts={
                                "priority": 1,
                                "attempts": 15,
                                "backoff": {"type": "exponential", "delay": 1000},
                            },
                            job_name=f"Update of {report_view.__name__} view"
                        )
        except Exception as e:
            log_exception(e)
            
    async def process_report_queue(self, job, token):
        job_data = job.data
        refresh_query = job_data['refresh_query']
        report_name = job_data['report_name']
        priority = job_data['priority']
        
        if not await DBMetrics().is_db_idle():
            raise Exception("System load is currently high, will retry later")
        
        conn = Tortoise.get_connection("default")

        await conn.execute_query(refresh_query)
        
        return f"{report_name} refreshed successfully"