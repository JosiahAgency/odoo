#!/usr/bin/env python3
import logging
import os
import sys
import threading

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# 1. Define Laravel-style Formatter
class AnsiColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_RED = "\033[41m"


class LaravelStyleFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: f"{AnsiColors.CYAN}DEBUG   {AnsiColors.RESET}",
        logging.INFO: f"{AnsiColors.GREEN}INFO    {AnsiColors.RESET}",
        logging.WARNING: f"{AnsiColors.YELLOW}WARN    {AnsiColors.RESET}",
        logging.ERROR: f"{AnsiColors.RED}{AnsiColors.BOLD}ERROR   {AnsiColors.RESET}",
        logging.CRITICAL: f"{AnsiColors.BG_RED}{AnsiColors.WHITE}{AnsiColors.BOLD}CRIT    {AnsiColors.RESET}",
    }

    APP_PATHS = ("eas-strathmore-odoo-addons", "josiah_odoo_addons", "coolsam-odoo-addons")

    def _format_stack(self, stack):
        out, skipped = [], 0
        for line in stack.splitlines():
            if "<frozen importlib" in line:
                skipped += 1
                continue
            if skipped:
                out.append(f"{AnsiColors.DIM}    ... {skipped} importlib frames hidden{AnsiColors.RESET}")
                skipped = 0
            if any(p in line for p in self.APP_PATHS):
                line = f"{AnsiColors.BOLD}{AnsiColors.YELLOW}{line}{AnsiColors.RESET}"
            elif line.lstrip().startswith("File "):
                line = f"{AnsiColors.DIM}{line}{AnsiColors.RESET}"
            out.append(line)
        if skipped:
            out.append(f"{AnsiColors.DIM}    ... {skipped} importlib frames hidden{AnsiColors.RESET}")
        return "\n".join(out)

    def format(self, record):
        record_time = self.formatTime(record, "%H:%M:%S")
        level_badge = self.LEVEL_COLORS.get(record.levelno, f"{record.levelname:<8}")
        message = record.getMessage()

        if "werkzeug" in record.name and ('"' in message):
            message = self._format_http_message(message)
        elif record.levelno >= logging.ERROR:
            message = f"{AnsiColors.RED}{message}{AnsiColors.RESET}"
        elif record.levelno >= logging.WARNING:
            message = f"{AnsiColors.YELLOW}{message}{AnsiColors.RESET}"

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            message += f"\n{AnsiColors.RED}{record.exc_text}{AnsiColors.RESET}"
        if record.stack_info:
            message += "\n" + self._format_stack(record.stack_info)

        pid = record.process
        db_name = getattr(record, 'dbname', None) or getattr(
            threading.current_thread(), "dbname", "?"
        )
        logger_name = record.name.replace("odoo.addons.", "", 1)

        prefix = (f"{AnsiColors.DIM}{record_time}{AnsiColors.RESET} {level_badge}"
                  f"{AnsiColors.DIM}[{pid}] {db_name}{AnsiColors.RESET} "
                  f"{AnsiColors.CYAN}{logger_name}{AnsiColors.RESET}:")
        return f"{prefix} {message}"

    def _format_http_message(self, message):
        parts = message.split('"')
        if len(parts) >= 3:
            client_ip = message.split(" - - ")[0]
            request_line = parts[1]
            status_code = parts[2].strip().split()[0]
            status_color = AnsiColors.GREEN
            if status_code.startswith("4"):
                status_color = AnsiColors.YELLOW
            elif status_code.startswith("5"):
                status_color = AnsiColors.RED
            return f"{AnsiColors.DIM}{client_ip}{AnsiColors.RESET} -> {request_line} {status_color}[{status_code}]{AnsiColors.RESET}"
        return message


# 2. Intercept setFormatter to prevent Odoo from overwriting our custom formatter
old_set_formatter = logging.Handler.setFormatter


def new_set_formatter(self, fmt):
    # Apply Laravel formatter to standard stream handlers, leave file handlers alone if any
    if isinstance(self, logging.StreamHandler) and not isinstance(self, logging.FileHandler):
        old_set_formatter(self, LaravelStyleFormatter())
    else:
        old_set_formatter(self, fmt)


logging.Handler.setFormatter = new_set_formatter

if __name__ == "__main__":
    # 3. Boot Odoo CLI
    import odoo.cli.command

    odoo.cli.command.main()
