import os

from textual import on
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, Button, Input, Static
from textual.containers import Vertical, Horizontal
from textual.worker import Worker, WorkerState

from tui_media_manager.imdb.utils import VideoFile
from tui_media_manager.imdb.utils import search_imdb_title
from tui_media_manager.messages import LogMessage


class VideoSearchQueryParamsModal(ModalScreen[WorkerState]):
    CSS = """
        VideoSearchQueryParamsModal {
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

    def __init__(self, video_file: VideoFile):
        super().__init__()
        self.video_file = video_file
        self.imdb_worker = None

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
            Label(f'IMDB Number: {self.video_file.imdb_tt}', id='imdb_id'),
            Input(default_input),
            Horizontal(
                Button('OK', compact=True, id='ok_id'),
                Button('Cancel', compact=True, id='cancel_id')
            )
        )

    # def on_mount(self) -> None:
    #     self.post_message(LogMessage(f'[VideoTitleSearchModal] Starting worker to fetch IMDB details for {self.video_file.imdb_tt}...'))
    #     self.imdb_worker = self.run_worker(search_imdb_title(self.video_file.imdb_tt))
    #     self.post_message(LogMessage(f'[VideoTitleSearchModal] Started worker to fetch IMDB details for {self.video_file.imdb_tt}'))
    #
    # @on(Button.Pressed, '#cancel_id')
    # def on_button_pressed(self, _event: Button.Pressed) -> None:
    #     self.post_message(LogMessage(f'[VideoTitleSearchModal] "Cancel" Button pressed'))
    #
    #     if self.imdb_worker and self.imdb_worker.state == WorkerState.RUNNING:
    #         self.post_message(LogMessage(f'[VideoTitleSearchModal] cancelling worker...'))
    #         self.imdb_worker.cancel()
    #         self.post_message(LogMessage(f'[VideoTitleSearchModal] worker cancelled'))
    #
    # def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
    #     self.post_message(LogMessage(f'[VideoTitleSearchModal] Received worker state change event: state={event.state}'))
    #
    #     if event.state == WorkerState.SUCCESS:
    #         self.post_message(LogMessage(f'[VideoTitleSearchModal] Final worker result: result={self.imdb_worker.result}'))
    #         self.dismiss(self.imdb_worker.result)
    #
    #     elif event.state in [WorkerState.CANCELLED, WorkerState.ERROR]:
    #         self.dismiss(None)
