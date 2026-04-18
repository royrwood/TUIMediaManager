from textual import on
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import TextArea, Button, Label
from textual.containers import Vertical, Horizontal

from tui_media_manager.imdb.utils import IMDBInfo
from tui_media_manager.messages import LogMessage


class ShowIMDBInfoModal(ModalScreen[IMDBInfo]):
    CSS = """
        ShowIMDBInfoModal {
            align: center middle;
        
            & > Vertical {
                min-width: 60vw;
                width: auto;
                height: auto;
                keyline: thin $primary;
        
                & > #plot_id {
                    width: 100%;
                    height: auto;
                    margin: 1;
                    padding: 0 2;
                }
        
                & > Horizontal {
                    width: 100%;
                    height: auto;
                    margin: 1;
                    padding: 1 2 1 2;
                    align-horizontal: right;
                
                    & > Button {
                        margin: 0 1;
                    }
                }
            }
        }
     """

    BINDINGS = [('escape', 'do_cancel', 'Cancel')]
    AUTO_FOCUS = "#accept_id"

    def __init__(self, imdb_info: IMDBInfo):
        super().__init__()
        self.imdb_info = imdb_info

        imdb_info_text = \
            f'IMDB  : {self.imdb_info.imdb_tt or ""}\n' + \
            f'Title : {self.imdb_info.imdb_name or ""}\n' + \
            f'Year  : {self.imdb_info.imdb_year or ""}\n' + \
            f'Rating: {self.imdb_info.imdb_rating or ""}\n' + \
            f'Genres: {self.imdb_info.imdb_genres or ""}\n' + \
            f'\n' + \
            (self.imdb_info.imdb_plot  or "")

        self.plot_text_area = TextArea(imdb_info_text, read_only=True, show_cursor=False, id='plot_id')
        self.plot_text_area.can_focus = False

    def compose(self) -> ComposeResult:
        yield Vertical(
            self.plot_text_area,
            Horizontal(
                Button('Accept', compact=True, id='accept_id'),
                Button('Close', compact=True, id='close_id')
            )
        )

    def action_do_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, '#accept_id')
    def accept_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ShowIMDBInfoModal] Button {event.button.id} pressed'))
        self.dismiss(self.imdb_info)

    @on(Button.Pressed, '#close_id')
    def cancel_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ShowIMDBInfoModal] Button {event.button.id} pressed'))
        self.dismiss(None)
