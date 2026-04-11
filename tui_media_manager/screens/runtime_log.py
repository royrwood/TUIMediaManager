import logging

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Log, Footer


LOGGER = logging.getLogger(__name__)
logging.basicConfig(filename='tui_media_manager.log', encoding='utf-8', level=logging.INFO)
LOGGER.info('Starting up...')


class RuntimeLogScreen(Screen):
    CSS = """
        Log {
            border: solid white;
            scrollbar-visibility: hidden;
        }
    """

    def __init__(self):
        super().__init__()
        self.logger = Log()

    def compose(self) -> ComposeResult:
        yield self.logger
        yield Footer()

    # def on_mount(self) -> None:
    #     self.info("Hello, World!")

    def info(self, message: str) -> None:
        LOGGER.info('[LogScreen] info: message="%s"', message)
        self.logger.write_line(message)
