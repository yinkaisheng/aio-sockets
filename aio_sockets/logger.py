from typing import Any, Protocol


class LoggerLike(Protocol):
    def log(self, level: str, message: str, **kwargs: Any) -> None:
        ...

    def debug(self, message: str, **kwargs: Any) -> None:
        ...

    def info(self, message: str, **kwargs: Any) -> None:
        ...

    def warning(self, message: str, **kwargs: Any) -> None:
        ...

    def error(self, message: str, **kwargs: Any) -> None:
        ...

    def critical(self, message: str, **kwargs: Any) -> None:
        ...


class StdoutLogger:
    def log(self, level: str, message: str) -> None:
        print(level, message)

    def debug(self, message: str) -> None:
        self.log("DEBUG", message)

    def info(self, message: str) -> None:
        self.log("INFO", message)

    def warning(self, message: str) -> None:
        self.log("WARNING", message)

    def error(self, message: str) -> None:
        self.log("ERROR", message)

    def critical(self, message: str) -> None:
        self.log("CRITICAL", message)
