from textual.message import Message


class LogMessage(Message):
    def __init__(self, message: str, level=0):
        super().__init__()
        self.message = message
        self.level = level


