import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from sqlalchemy.sql import extract

from app.core.database import SessionLocal
from app.models.scheduled_job import ScheduledNotificationJob
from app.models.notification_delivery_queue import NotificationDeliveryQueue
from app.models.push_retry_queue import PushRetryQueue

logger = logging.getLogger(__name__)


class NotificationMetricsService:

    @staticmethod
    def get_performance_metrics(db: Session) -> dict:
        """
        Query database to calculate performance metrics (average, P95, P99, and maximum delays)
        for scheduling, processing, push delivery, and websocket delivery.
        """
        query = text("""
            SELECT 
                COALESCE(AVG(EXTRACT(EPOCH FROM (delivery_started_at - scheduled_for))), 0.0) AS avg_scheduling_delay,
                COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (delivery_started_at - scheduled_for))), 0.0) AS p95_scheduling_delay,
                COALESCE(percentile_cont(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (delivery_started_at - scheduled_for))), 0.0) AS p99_scheduling_delay,
                COALESCE(MAX(EXTRACT(EPOCH FROM (delivery_started_at - scheduled_for))), 0.0) AS max_scheduling_delay,
                
                COALESCE(AVG(EXTRACT(EPOCH FROM (delivery_started_at - created_at))), 0.0) AS avg_processing_delay,
                COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (delivery_started_at - created_at))), 0.0) AS p95_processing_delay,
                COALESCE(percentile_cont(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (delivery_started_at - created_at))), 0.0) AS p99_processing_delay,
                COALESCE(MAX(EXTRACT(EPOCH FROM (delivery_started_at - created_at))), 0.0) AS max_processing_delay,

                COALESCE(AVG(EXTRACT(EPOCH FROM (delivered_at - delivery_started_at))), 0.0) FILTER (WHERE channel = 'PUSH' AND status = 'SENT') AS avg_push_delivery_delay,
                COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (delivered_at - delivery_started_at))) FILTER (WHERE channel = 'PUSH' AND status = 'SENT'), 0.0) AS p95_push_delivery_delay,
                COALESCE(percentile_cont(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (delivered_at - delivery_started_at))) FILTER (WHERE channel = 'PUSH' AND status = 'SENT'), 0.0) AS p99_push_delivery_delay,
                COALESCE(MAX(EXTRACT(EPOCH FROM (delivered_at - delivery_started_at))) FILTER (WHERE channel = 'PUSH' AND status = 'SENT'), 0.0) AS max_push_delivery_delay,

                COALESCE(AVG(EXTRACT(EPOCH FROM (delivered_at - delivery_started_at))), 0.0) FILTER (WHERE channel = 'WEBSOCKET' AND status = 'SENT') AS avg_websocket_delivery_delay,
                COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (delivered_at - delivery_started_at))) FILTER (WHERE channel = 'WEBSOCKET' AND status = 'SENT'), 0.0) AS p95_websocket_delivery_delay,
                COALESCE(percentile_cont(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (delivered_at - delivery_started_at))) FILTER (WHERE channel = 'WEBSOCKET' AND status = 'SENT'), 0.0) AS p99_websocket_delivery_delay,
                COALESCE(MAX(EXTRACT(EPOCH FROM (delivered_at - delivery_started_at))) FILTER (WHERE channel = 'WEBSOCKET' AND status = 'SENT'), 0.0) AS max_websocket_delivery_delay
            FROM notification_delivery_queue
        """)
        
        try:
            result = db.execute(query).fetchone()
            
            # Map row keys/values
            metrics = {
                "scheduling_delay": {
                    "average_seconds": round(float(result[0] or 0.0), 3),
                    "p95_seconds": round(float(result[1] or 0.0), 3),
                    "p99_seconds": round(float(result[2] or 0.0), 3),
                    "max_seconds": round(float(result[3] or 0.0), 3)
                },
                "processing_delay": {
                    "average_seconds": round(float(result[4] or 0.0), 3),
                    "p95_seconds": round(float(result[5] or 0.0), 3),
                    "p99_seconds": round(float(result[6] or 0.0), 3),
                    "max_seconds": round(float(result[7] or 0.0), 3)
                },
                "push_delivery_delay": {
                    "average_seconds": round(float(result[8] or 0.0), 3),
                    "p95_seconds": round(float(result[9] or 0.0), 3),
                    "p99_seconds": round(float(result[10] or 0.0), 3),
                    "max_seconds": round(float(result[11] or 0.0), 3)
                },
                "websocket_delivery_delay": {
                    "average_seconds": round(float(result[12] or 0.0), 3),
                    "p95_seconds": round(float(result[13] or 0.0), 3),
                    "p99_seconds": round(float(result[14] or 0.0), 3),
                    "max_seconds": round(float(result[15] or 0.0), 3)
                }
            }
            return metrics
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")
            return {}

    @staticmethod
    def get_worker_health_stats(db: Session) -> dict:
        """
        Fetch worker health parameters including queue sizes, pending/processing/failed counts,
        average processing time, and current throughput.
        """
        try:
            # Scheduled Notification Jobs counts
            pending_jobs = db.query(ScheduledNotificationJob).filter(ScheduledNotificationJob.status == "PENDING").count()
            processing_jobs = db.query(ScheduledNotificationJob).filter(ScheduledNotificationJob.status == "PROCESSING").count()
            failed_jobs = db.query(ScheduledNotificationJob).filter(ScheduledNotificationJob.status == "FAILED").count()

            # Delivery Queue counts
            pending_deliveries = db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.status == "PENDING").count()
            processing_deliveries = db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.status == "PROCESSING").count()
            failed_deliveries = db.query(NotificationDeliveryQueue).filter(NotificationDeliveryQueue.status == "FAILED").count()

            # Specific channel queue sizes (Pending + Processing)
            push_queue_size = db.query(NotificationDeliveryQueue).filter(
                NotificationDeliveryQueue.channel == "PUSH",
                NotificationDeliveryQueue.status.in_(["PENDING", "PROCESSING"])
            ).count()

            websocket_queue_size = db.query(NotificationDeliveryQueue).filter(
                NotificationDeliveryQueue.channel == "WEBSOCKET",
                NotificationDeliveryQueue.status.in_(["PENDING", "PROCESSING"])
            ).count()

            # Retry queue size (Pending status in PushRetryQueue)
            retry_queue_size = db.query(PushRetryQueue).filter(PushRetryQueue.status == "PENDING").count()

            # Average processing time (creation to delivery) for sent deliveries
            avg_processing_time = db.query(
                func.avg(extract('epoch', NotificationDeliveryQueue.delivered_at - NotificationDeliveryQueue.created_at))
            ).filter(NotificationDeliveryQueue.status == "SENT").scalar() or 0.0

            # Throughput per minute (calculated over last 10 minutes)
            ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
            sent_in_last_10_min = db.query(NotificationDeliveryQueue).filter(
                NotificationDeliveryQueue.status == "SENT",
                NotificationDeliveryQueue.delivered_at >= ten_minutes_ago
            ).count()

            throughput_per_min = round(sent_in_last_10_min / 10.0, 2)

            return {
                "scheduled_jobs": {
                    "pending": pending_jobs,
                    "processing": processing_jobs,
                    "failed": failed_jobs
                },
                "delivery_queue": {
                    "pending": pending_deliveries,
                    "processing": processing_deliveries,
                    "failed": failed_deliveries,
                    "push_queue_size": push_queue_size,
                    "websocket_queue_size": websocket_queue_size,
                    "retry_queue_size": retry_queue_size
                },
                "metrics": {
                    "average_processing_time_seconds": round(float(avg_processing_time), 3),
                    "throughput_per_minute": throughput_per_min
                }
            }
        except Exception as e:
            logger.error(f"Failed to fetch worker health stats: {e}")
            return {}


# Global service instance
notification_metrics_service = NotificationMetricsService()
