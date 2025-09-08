import logging
from typing import Optional, Union


class Logger:
    """Provide a unified logger accessor and optional configuration.

    Usage:
        - In classes mixing this in, call Logger.__init__(self, logger=...) or
          rely on a parent (e.g., Hypercube) to do so.
        - Use self.log().info("message") to log.

    Behavior:
        - If logger is True, enable a basic INFO-level config with a simple format
          only when the root logger has no handlers, then use a module-named logger.
        - If logger is a logging.Logger, use it.
        - Otherwise, do not configure logging globally; log() will fall back to a
          module-named logger that inherits application settings.
    """

    def __init__(self, logger: Optional[Union[logging.Logger, bool]] = None) -> None:
        if isinstance(logger, bool):
            if logger:
                # Enable a basic config only if no handlers exist
                if not logging.getLogger().handlers:
                    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
                # Use a module-named logger for the concrete class
                self._log = logging.getLogger(self.__class__.__module__)
            else:
                # Create a per-instance silent logger (no propagation, NullHandler)
                silent_name = f"{self.__class__.__module__}.{id(self)}.silent"
                lgr = logging.getLogger(silent_name)
                lgr.handlers.clear()
                lgr.addHandler(logging.NullHandler())
                lgr.propagate = False
                lgr.setLevel(logging.CRITICAL)
                self._log = lgr
        elif isinstance(logger, logging.Logger):
            self._log = logger
        else:
            # Always set a module-named logger so direct self._log usage is safe
            self._log = logging.getLogger(self.__class__.__module__)

    def log(self) -> logging.Logger:
        logger = getattr(self, "_log", None)
        if logger is not None:
            return logger
        # Fallback to a logger named after the class' module for sensible defaults
        return logging.getLogger(self.__class__.__module__)
