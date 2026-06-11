"""
apps/notifications/tasks.py
---------------------------
Placeholder for asynchronous notification tasks.
"""
import logging

logger = logging.getLogger(__name__)


class MockAsyncNotificationTask:
    """
    Mock task to allow .delay() calls without a fully configured Celery broker.
    Once Celery is properly integrated, this should be replaced with @shared_task.
    """
    def delay(self, event_type, subscriber_id, *args, **kwargs):
        logger.info(f"Mock send_notification_async: {event_type} for subscriber {subscriber_id}")
        return self(event_type, subscriber_id, *args, **kwargs)

    def __call__(self, event_type, subscriber_id, *args, **kwargs):
        pass


send_notification_async = MockAsyncNotificationTask()
