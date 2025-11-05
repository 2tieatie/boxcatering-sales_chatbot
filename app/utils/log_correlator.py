from app.database import get_db
from app.models.prompt_log import PromptLog


class LogCorrelator:
    def get_full_request_flow(self, correlation_id: str):
        """Get complete request flow from all logging systems."""
        return {
            "database_log": self.get_database_log(correlation_id),
            "file_logs": self.get_file_logs(correlation_id),
            "console_logs": self.get_console_logs(correlation_id),
        }

    def get_database_log(self, correlation_id: str):
        """Get database log entry."""
        db = next(get_db())
        return (
            db.query(PromptLog)
            .filter(PromptLog.correlation_id == correlation_id)
            .first()
        )

    def get_file_logs(self, correlation_id: str):
        """Get related file log entries."""
        # Parse log files for entries with this correlation_id
        pass
