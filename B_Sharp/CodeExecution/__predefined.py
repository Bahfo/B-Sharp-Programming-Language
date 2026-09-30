# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# The source code of B_Sharp Programming Language.
# The code is guarded and licensed under the GPLv3 License.
# ---------------------------------------------------------------
# Module: __predefined: Functionality for predefined macros in B#

from typing import Literal
from platform import system


def __match_macro_to_os(macro_os_version_name: str):
    os_macros = {
        "__GNU_LINUX": "Linux",
        "__NT_KERNEL": "Windows",
        "__DARWIN": "Darwin",
    }
    return system() == os_macros.get(macro_os_version_name, macro_os_version_name)


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
