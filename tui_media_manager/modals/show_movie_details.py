from textual import on
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import TextArea, Button
from textual.containers import Vertical, Horizontal
from textual.worker import WorkerState

from tui_media_manager.imdb.utils import VideoFile, IMDBInfo
from tui_media_manager.messages import LogMessage
from tui_media_manager.modals.video_search_query_params import VideoSearchQueryParamsModal


class ShowMovieDetailsModal(ModalScreen[WorkerState]):
    CSS = """
        ShowMovieDetailsModal {
            align-horizontal: center;
            align-vertical: middle;
        
            & > Vertical {
                width: 80vw;
                height: auto;
                # padding: 1 2;
                keyline: thin $primary;
                # offset-y: 25vh;
                # background: yellow;
        
                & > #file_path_id {
                    width: 100%;
                    height: auto;
                    margin: 1;
                    # padding: 1 2 1 2;
                    # background: blue;
                }
        
                & > #plot_id {
                    width: 100%;
                    height: auto;
                    margin: 1;
                    padding: 1 2 1 2;
                    # background: red;
                }
        
                & > Horizontal {
                    width: 100%;
                    height: auto;
                    margin: 1;
                    padding: 1 2 1 2;
                    align-horizontal: right;
                    # background: green;
                }
            }
        }
     """

    BINDINGS = [('escape', 'cancel_menu', 'Cancel Menu')]
    AUTO_FOCUS = "#ok_id"

    def __init__(self, video_file: VideoFile):
        super().__init__()
        self.video_file = video_file
        self.imdb_worker = None
        self.file_text_area = TextArea(self.video_file.file_path, read_only=True, show_cursor=False, id='file_path_id')
        self.file_text_area.can_focus = False
        self.plot_text_area = TextArea(self.video_file.imdb_plot, read_only=True, show_cursor=False, id='plot_id')
        self.plot_text_area.can_focus = False

    def compose(self) -> ComposeResult:
        yield Vertical(
            self.file_text_area,
            self.plot_text_area,
            Horizontal(
                Button('Search IMDB', compact=True, id='search_imdb_id'),
                Button('OK', compact=True, id='ok_id')
            )
        )

    def action_cancel_menu(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, '#search_imdb_id')
    def search_imdb_button_pressed(self, event: Button.Pressed) -> None:
        def _video_content_fetch_complete_callback(worker_state: WorkerState) -> None:
            if worker_state == WorkerState.SUCCESS:
                text_area: TextArea = self.query_one('#plot_id', TextArea)
                text_area.text = self.video_file.imdb_plot

        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed; showing VideoFetchContentModal'))
        self.app.push_screen(VideoSearchQueryParamsModal(self.video_file), _video_content_fetch_complete_callback)

    @on(Button.Pressed, '#ok_id')
    def ok_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed'))
        self.dismiss(WorkerState.SUCCESS)
