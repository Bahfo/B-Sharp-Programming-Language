from B_Sharp.tokens import *


def format(
    error_message: list,
    error_column,
    error_type,
    error_line,
    error_code,
    error_hint,
    file,
):
    """
    Error formatting function to produce formatted rich-syntax error.

    Expects a valid error type and the list of error message lines.
    """

    column = max(0, int(error_column) - 1)
    pointer = " " * column + "^"

    # Use 3 spaces after '│' to match the 4-char prefix of '├─> ' and '│   '
    formatted_msgs = "\n".join(f"│   {line}" for line in error_message)

    result = f"""{BOLD_RED}Error: {error_type}{RESET}
╭─ {file}: in Line {error_line}: Col {error_column}
│  An error has occurred. The following message explains it: 
│
├─> {error_code}
│   {BOLD_RED}{pointer}{RESET}
{formatted_msgs}
│
╰─> {BLUE}HINT{RESET}: {error_hint}
"""
    return result


def format_warning(
    warning_message: list,
    warning_column,
    warning_type,
    warning_line,
    warning_code,
    warning_hint,
    file,
):
    """
    Warning formatting function – yellow header instead of red.
    """

    column = max(0, int(warning_column) - 1)
    pointer = " " * column + "^"

    formatted_msgs = "\n".join(f"│   {line}" for line in warning_message)

    result = f"""{BOLD_YELLOW}Warning: {warning_type}{RESET}
╭─ {file}: in Line {warning_line}: Col {warning_column}
│  A warning has been raised: 
│
├─> {warning_code}
│   {BOLD_YELLOW}{pointer}{RESET}
{formatted_msgs}
│
╰─> {BLUE}HINT{RESET}: {warning_hint}
"""
    return result
