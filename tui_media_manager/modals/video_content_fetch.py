from textual import on
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal
from textual.worker import Worker, WorkerState

from tui_media_manager.imdb.utils import VideoFile
from tui_media_manager.messages import LogMessage
from tui_media_manager.imdb.utils import get_imdb_details


class VideoFetchContentModal(ModalScreen[WorkerState]):
    CSS = """
        VideoFetchContentModal {
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
                                
                & > Horizontal {
                    width: 100%;
                    height: auto;
                    align-horizontal: right;
                }
            }
        }   
     """

    def __init__(self, video_file: VideoFile):
        super().__init__()
        self.video_file = video_file
        self.imdb_worker = None

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(f'Fetching IMDB info for {self.video_file.imdb_name} [{self.video_file.imdb_tt}]', id='message_id'),
            Horizontal(
                Button('Cancel', compact=True, id='cancel_id')
            )
        )

    def on_mount(self) -> None:
        self.post_message(LogMessage(f'[VideoFetchContentModal] Starting worker to fetch IMDB details for {self.video_file.imdb_tt}...'))
        self.imdb_worker = self.run_worker(get_imdb_details(self.video_file.imdb_tt))
        self.post_message(LogMessage(f'[VideoFetchContentModal] Started worker to fetch IMDB details for {self.video_file.imdb_tt}'))

    @on(Button.Pressed, '#cancel_id')
    def on_button_pressed(self, _event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[VideoFetchContentModal] "Cancel" Button pressed'))

        if self.imdb_worker and self.imdb_worker.state == WorkerState.RUNNING:
            self.post_message(LogMessage(f'[VideoFetchContentModal] cancelling worker...'))
            self.imdb_worker.cancel()
            self.post_message(LogMessage(f'[VideoFetchContentModal] worker cancelled'))

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        self.post_message(LogMessage(f'[VideoFetchContentModal] Received worker state change event: state={event.state}'))

        if event.state == WorkerState.SUCCESS:
            self.post_message(LogMessage(f'[VideoFetchContentModal] Final worker result: result={self.imdb_worker.result}'))
            self.video_file.imdb_plot = self.imdb_worker.result.imdb_plot

        if event.state in [WorkerState.CANCELLED, WorkerState.ERROR, WorkerState.SUCCESS]:
            self.dismiss(event.state)
