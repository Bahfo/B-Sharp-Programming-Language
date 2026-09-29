# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# The source code of B_Sharp Programming Language.
# The code is guarded and licensed under the GPLv3 License.
# ---------------------------------------------------------------
# Module: __predefined: Functionality for predefined macros in B#

from typing import Literal
from platform import system


def __match_macro_to_os() -> Literal["__DARWIN", "__NT_KERNEL", "__GNU_LINUX"] | None:
    """
    Matches the operating system's version obtained via `system()`
    to B-Sharp's OS-specific predefined macros.

    Expands to: B-Sharp predefined macros: `__DARWIN`, `__NT_KERNEL`,
    `__GNU_LINUX`
    """

    __os_version = system()

    match __os_version:
        case "Darwin":
            return "__DARWIN"
        case "Windows":
            return "__NT_KERNEL"
        case "Linux":
            return "__GNU_LINUX"


def __return_current_line_number() -> int:
    """
    Useful to return the line number of currently executing program.

    Once invoked in B-Sharp codes. It returns the current line of its
    file. Doesn't return the line number based on how much files are
    executed. But looks instead at the currently running file, and then
    returns its line number.

    Expands to: B-Sharp predefined macro: `__LINE__`
    """


def __return_file_name() -> str:
    """
    Useful to return the file name and path of currently executing
    file within the program.

    Once invoked, it returns which file name is currently executing
    within a B-Sharp program.

    Expands to: B-Sharp predefined macro: `__FILE__`
    """
