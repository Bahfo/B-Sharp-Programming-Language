class Position:
    """
    A helper class to calculate the index, line, and column with the
    exact file name and text for each token specified.

    Useful upon displaying error messages.

    Default Arguments:
        `index`:
        `line`:
        `col`:
        `file_name`:
        `file_text`:
    """

    def __init__(
        self,
        index,
        line,
        col,
        file_name,
        file_text,
    ):
        self.index = index
        self.line = line
        self.col = col
        self.file_name = file_name
        self.file_text = file_text

    def forward(self, current_char=None):
        self.index += 1
        self.col += 1

        if current_char == "\n":
            self.line += 1
            self.col = 0

        return self

    def copy(self):
        return Position(
            self.index,
            self.line,
            self.col,
            self.file_name,
            self.file_text,
        )
