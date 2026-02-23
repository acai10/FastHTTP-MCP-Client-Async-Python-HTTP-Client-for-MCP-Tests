import logging


class ColorFormatter(logging.Formatter):
    """
    Formatter that prints:
    - INFO    logs in green
    - WARNING logs in magenta
    - ERROR   and CRITICAL logs in red
    - others  without color
    """

    GREEN = "\x1b[32m"
    MAGENTA = "\x1b[35m"
    RED = "\x1b[31m"
    RESET = "\x1b[0m"

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)

        if record.levelno == logging.INFO:
            color = self.GREEN
        elif record.levelno == logging.WARNING:
            color = self.MAGENTA
        elif record.levelno in (logging.ERROR, logging.CRITICAL):
            color = self.RED
        else:
            color = ""

        if color:
            return f"{color}{msg}{self.RESET}"
        return msg


def setup_colored_logger(level: int = logging.INFO) -> logging.Logger:
    """
    Configure root logger with ColorFormatter and return it.

    Colors:
    - INFO    -> green
    - WARNING -> magenta
    - ERROR   -> red
    - CRITICAL-> red
    """
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter("[%(levelname)s] %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    return root
