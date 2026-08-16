class Error:
    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def as_string(self):
        result = f"{self.error_name} :\n{self.details}\n"
        if self.pos_start is None:
            return result
        result += f"File {self.pos_start.file_name}, Ln: {self.pos_start.line + 1}"
        return result


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
