class MonitorError(Exception):
    """Base class for monitor-related errors."""


class FetchError(MonitorError):
    """Raised when a source cannot be fetched."""


class ParseError(MonitorError):
    """Raised when a source cannot be parsed into holdings."""


class ValidationError(MonitorError):
    """Raised when a parsed snapshot fails validation."""


class StorageError(MonitorError):
    """Raised when persistence fails."""


class NotifyError(MonitorError):
    """Raised when a notification cannot be delivered."""
