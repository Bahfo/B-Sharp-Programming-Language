class Error:
    def __init__(self, pos_start, pos_end, error_code, context=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_code = error_code
        self.context = context or {}
        
        # Load error info from catalog
        from B_Sharp.Errors.error_catalog import ERROR_CATALOG
        error_info = ERROR_CATALOG.get(error_code, {})
        self.error_name = error_info.get("name", "Unknown Error")
        self.hint = error_info.get("hint", "check the code at the indicated position")
        
        # Format the message with context
        try:
            self.details = error_info.get("message", "An error occurred").format(**self.context)
        except (KeyError, IndexError, ValueError):
            self.details = error_info.get("message", "An error occurred")

    def as_string(self):
        from B_Sharp.Errors.format import format

        if self.pos_start is None:
            return f"{self.error_name} ({self.error_code}):\n{self.details}\n"

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

        return format(
            error_message=details_lines,
            error_column=self.pos_start.col + 1,
            error_type=f"{self.error_name} ({self.error_code})",
            error_line=self.pos_start.line + 1,
            error_code=source_line,
            error_hint=self.hint,
            file=self.pos_start.file_name,
        )


class IllegalCharacterError(Error):
    def __init__(self, pos_start, pos_end, char):
        super().__init__(pos_start, pos_end, "LEX001", {"char": char})

    def __str__(self):
        return self.as_string()


class B_SharpSyntaxError(Error):
    def __init__(self, pos_start, pos_end, error_code, context=None):
        super().__init__(pos_start, pos_end, error_code, context)

    def __str__(self):
        return self.as_string()


class RunTimeError(Error):
    def __init__(self, pos_start, pos_end, error_code, context=None):
        super().__init__(pos_start, pos_end, error_code, context)

    def __str__(self):
        return self.as_string()


class AssignmentError(Error):
    def __init__(self, pos_start, pos_end, error_code, context=None):
        super().__init__(pos_start, pos_end, error_code, context)

    def __str__(self):
        return self.as_string()


class ModificationError(Error):
    def __init__(self, pos_start, pos_end, error_code, context=None):
        super().__init__(pos_start, pos_end, error_code, context)

    def __str__(self):
        return self.as_string()


class EmptinessUnmatchedError(Error):
    def __init__(self, pos_start, pos_end, error_code, context=None):
        super().__init__(pos_start, pos_end, error_code, context)

    def __str__(self):
        return self.as_string()


class ComparisonError(Error):
    def __init__(self, pos_start, pos_end, error_code, context=None):
        super().__init__(pos_start, pos_end, error_code, context)

    def __str__(self):
        return self.as_string()


class DoubleFloatingAssignedError(Error):
    def __init__(self, pos_start, pos_end):
        super().__init__(pos_start, pos_end, "LEX002")

    def __str__(self):
        return self.as_string()


class CircularImportError(Error):
    def __init__(self, pos_start, pos_end, file_path):
        super().__init__(pos_start, pos_end, "IMP001", {"file_path": file_path})

    def __str__(self):
        return self.as_string()


class BSharpMathError(Error):
    def __init__(self, pos_start, pos_end):
        super().__init__(pos_start, pos_end, "MTH001")

    def __str__(self):
        return self.as_string()


class ShadowingError(Error):
    def __init__(self, pos_start, pos_end, param_name, func_name):
        super().__init__(pos_start, pos_end, "SHD001", {
            "param_name": param_name,
            "func_name": func_name
        })

    def __str__(self):
        return self.as_string()


class Warning:
    def __init__(self, pos_start, pos_end, warning_code, context=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.warning_code = warning_code
        self.context = context or {}
        
        # Load warning info from catalog
        from B_Sharp.Errors.error_catalog import ERROR_CATALOG
        warning_info = ERROR_CATALOG.get(warning_code, {})
        self.warning_name = warning_info.get("name", "Unknown Warning")
        self.hint = warning_info.get("hint", "check the code at the indicated position")
        
        # Format the message with context
        try:
            self.details = warning_info.get("message", "A warning occurred").format(**self.context)
        except (KeyError, IndexError, ValueError):
            self.details = warning_info.get("message", "A warning occurred")

    def as_string(self):
        from B_Sharp.Errors.format import format_warning

        if self.pos_start is None:
            return f"{self.warning_name} ({self.warning_code}):\n{self.details}\n"

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
            warning_type=f"{self.warning_name} ({self.warning_code})",
            warning_line=self.pos_start.line + 1,
            warning_code=source_line,
            warning_hint=self.hint,
            file=self.pos_start.file_name,
        )

    def __str__(self):
        return self.as_string()


class UnreachableCodeWarning(Warning):
    def __init__(self, pos_start, pos_end, func_name):
        super().__init__(pos_start, pos_end, "WRN001", {"func_name": func_name})


class PrecisionLossWarning(Warning):
    def __init__(self, pos_start, pos_end, base, exponent):
        super().__init__(pos_start, pos_end, "WRN002", {
            "base": base,
            "exponent": exponent
        })
