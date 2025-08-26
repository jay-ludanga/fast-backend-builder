from datetime import datetime, timezone

from fast_backend_builder.notifications.service import NotificationService
from fast_backend_builder.utils.error_logging import log_exception


async def log_user_activity(user_id, username: str, entity: str, action: str, details: str):
    """
    Logs user activity to a Logger Queue.
    @param user_id: user id
    @param username: user email/username
    @param entity: user entity/Model Verbose Name
    @param action: user action (ADDITION, DELETE, CHANGE)
    @param details: log details
    """
    try:
        await NotificationService.get_instance().put_message_on_queue('AuditLogs', {
            'user_id': str(user_id),
            'username': username,
            'entity': entity,
            'action': action,
            'details': details,
            'action_date': datetime.now(timezone.utc).isoformat()
        }, 'LogActivity')
    except Exception as e:
        log_exception(e)
