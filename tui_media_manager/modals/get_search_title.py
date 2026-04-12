import os

from textual import on
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, Button, Input
from textual.containers import Vertical, Horizontal

from tui_media_manager.imdb.utils import VideoFile
from tui_media_manager.messages import LogMessage


class GetSearchTitleModal(ModalScreen[str]):
    CSS = """
        GetSearchTitleModal {
            align-horizontal: center;
            
            & > Vertical {
                width: auto;
                height: auto;
                offset-y: 25vh;
                border: round $primary;
                padding: 1 2;
                
                & > Label {
                    margin-bottom: 1;
                }
                
                & > Input {
                    margin-bottom: 1;
                }
                                
                & > Horizontal {
                    width: 100%;
                    height: auto;
                    align-horizontal: right;
                
                    & > Button {
                        margin: 0 1;
                    }
                }
            }
        }   
     """

    BINDINGS = [('escape', 'cancel_button_pressed', 'Cancel')]

    def __init__(self, video_file: VideoFile):
        super().__init__()
        self.video_file = video_file

    def compose(self) -> ComposeResult:
        if self.video_file.imdb_name:
            default_input = f'{self.video_file.imdb_name} {self.video_file.imdb_year}'.strip()
        elif self.video_file.scrubbed_file_name:
            default_input = f'{self.video_file.scrubbed_file_name} {self.video_file.scrubbed_file_year}'.strip()
        elif self.video_file.imdb_tt:
            default_input = self.video_file.imdb_tt
        else:
            default_input = ''

        filename = os.path.split(self.video_file.file_path)[1]

        yield Vertical(
            Label(f'Enter title or IMDB Number', id='message_id'),
            Label(f'Filename: {filename}', id='file_id'),
            # Label(f'IMDB Number: {self.video_file.imdb_tt}', id='imdb_id'),
            Input(default_input),
            Horizontal(
                Button('Search IMDB', compact=True, id='search_id'),
                Button('Cancel', compact=True, id='cancel_id')
            )
        )

    @on(Button.Pressed, '#cancel_id')
    def action_cancel_button_pressed(self, _event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[GetSearchTitleModal] "Cancel" Button pressed'))
        self.dismiss(None)

    @on(Button.Pressed, '#search_id')
    def search_button_pressed(self, _event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[GetSearchTitleModal] "Search IMDB" Button pressed'))
        input_widget = self.query_one('Input', Input)
        self.dismiss(input_widget.value)