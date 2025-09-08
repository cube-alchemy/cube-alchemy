# Logger API

Provide a unified accessor for logging within the hypercube and mixins.

## log

```python
log() -> logging.Logger
```

Return a logger for the instance. If `self._log` exists, it is returned; otherwise a module-named logger is provided.
