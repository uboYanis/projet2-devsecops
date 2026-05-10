import schedule
import time
import logging
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","trace_id":"%(trace_id)s","msg":"%(message)s"}'
)

class TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = getattr(record, 'trace_id', '-')
        return True

logger = logging.getLogger(__name__)
logger.addFilter(TraceFilter())

def archive_old_notes():
    trace_id = str(uuid.uuid4())
    logger.info("Worker: archivage des notes de plus de 30 jours", extra={"trace_id": trace_id})

schedule.every(10).minutes.do(archive_old_notes)

if __name__ == "__main__":
    logger.info("Worker démarré", extra={"trace_id": "-"})
    while True:
        schedule.run_pending()
        time.sleep(1)
