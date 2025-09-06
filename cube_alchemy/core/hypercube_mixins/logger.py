import logging


class Logger:
    """Provide a unified logger accessor.

    Usage:
        self.log().info("message")
    Prefers an instance-level logger at self._log when present; falls back to a
    module-specific logger based on the instance's defining module.
    """

    def log(self) -> logging.Logger:
        logger = getattr(self, "_log", None)
        if logger is not None:
            return logger
        # Fallback to a logger named after the class' module for sensible defaults
        return logging.getLogger(self.__class__.__module__)
