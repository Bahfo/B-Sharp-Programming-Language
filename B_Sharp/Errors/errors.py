class Error:
    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def as_string(self):
        from B_Sharp.Errors.format import format
        from B_Sharp.Errors.error_hints import HINTS

        if self.pos_start is None:
            return f"{self.error_name} :\n{self.details}\n"

        source_lines = self.pos_start.file_text.split("\n")
        source_line = (
            source_lines[self.pos_start.line]
            if self.pos_start.line < len(source_lines)
            else ""
        )

        # Convert error details string into a list of lines for error_message
        details_lines = (
            self.details.split("\n")
            if isinstance(self.details, str)
            else [str(self.details)]
        )

        return format(
            error_message=details_lines,
            error_column=self.pos_start.col + 1,
            error_type=self.error_name,
            error_line=self.pos_start.line + 1,
            error_code=source_line,
            error_hint=HINTS.get(
                self.error_name, "check the code at the indicated position"
            ),
            file=self.pos_start.file_name,
        )


class IllegalCharacterError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Illegal Character", details)

    def __str__(self):
        return self.as_string()


class B_SharpSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Syntax Error", details)

    def __str__(self):
        return self.as_string()


class RunTimeError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "RunTime Error", details)

    def __str__(self):
        return self.as_string()


class AssignmentError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Uncaught Assignment Error.", details)

    def __str__(self):
        return self.as_string()


class ModificationError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Uncaught Modification Error.", details)

    def __str__(self):
        return self.as_string()


class EmptinessUnmatchedError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Assigning to Empty Error.", details)

    def __str__(self):
        return self.as_string()


class ComparisonError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Comparison Syntax Error.", details)

    def __str__(self):
        return self.as_string()


class DoubleFloatingAssignedError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Double Floating Assigned Error.", details)

    def __str__(self):
        return self.as_string()


class CircularImportError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Circular Import Error.", details)

    def __str__(self):
        return self.as_string()


class BSharpMathError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Unexpected Mathematical Error.", details)

    def __str__(self):
        return self.as_string()


class ShadowingError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Shadowing Error", details)

    def __str__(self):
        return self.as_string()


class Warning:
    def __init__(self, pos_start, pos_end, warning_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.warning_name = warning_name
        self.details = details

    def as_string(self):
        from B_Sharp.Errors.format import format_warning
        from B_Sharp.Errors.error_hints import HINTS

        if self.pos_start is None:
            return f"{self.warning_name} :\n{self.details}\n"

        source_lines = self.pos_start.file_text.split("\n")
        source_line = (
            source_lines[self.pos_start.line]
            if self.pos_start.line < len(source_lines)
            else ""
        )

        details_lines = (
            self.details.split("\n")
            if isinstance(self.details, str)
            else [str(self.details)]
        )

        return format_warning(
            warning_message=details_lines,
            warning_column=self.pos_start.col + 1,
            warning_type=self.warning_name,
            warning_line=self.pos_start.line + 1,
            warning_code=source_line,
            warning_hint=HINTS.get(
                self.warning_name, "check the code at the indicated position"
            ),
            file=self.pos_start.file_name,
        )

    def __str__(self):
        return self.as_string()


class UnreachableCodeWarning(Warning):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Unreachable Code", details)


class PrecisionLossWarning(Warning):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "Precision Loss", details)
