from .file_logger import get_logger

file_logger = get_logger(name="file_logger", log_file="./logger/app.log")

__all__ = [
    "file_logger",
]
