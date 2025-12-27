#!/usr/bin/python
import traceback
import sys

def format_error_info(exc_type, exc_value, exc_traceback):
    """
    Format error information in GNU format (file:line:column).
    """
    tb_list = traceback.extract_tb(exc_traceback)
    formatted_lines = []
    for filename, lineno, funcname, line in reversed(tb_list):
        formatted_lines.append(f"{filename}:{lineno}:{line.strip()}")
    error_message = f"{exc_type.__name__}: {exc_value}\n" + "\n".join(formatted_lines)
    return error_message

def custom_error_handler(exc_type, exc_value, exc_traceback):
    """
    Custom error handler to print errors in GNU format.
    """
    error_message = format_error_info(exc_type, exc_value, exc_traceback)
    sys.stderr.write(error_message + "\n")

# Set the custom error handler
sys.excepthook = custom_error_handler

# Example usage to trigger an error
try:
    raise ValueError("This is a sample error") from None
except Exception:
    pass  # The error will be handled by our custom error handler
