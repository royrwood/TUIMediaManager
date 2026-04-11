from textual import on
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import TextArea, Button
from textual.containers import Vertical, Horizontal
from textual.worker import WorkerState

from tui_media_manager.imdb.utils import VideoFile, IMDBInfo
from tui_media_manager.messages import LogMessage
from tui_media_manager.modals.video_content_fetch import VideoFetchContentModal
from tui_media_manager.modals.video_search_title import VideoSearchTitleModal


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

    def compose(self) -> ComposeResult:
        yield Vertical(
            TextArea(self.video_file.file_path, read_only=True, show_cursor=False, id='file_path_id'),
            TextArea(self.video_file.imdb_plot, read_only=True, show_cursor=False, id='plot_id'),
            Horizontal(
                Button('Fetch Details', compact=True, id='fetch_details_id'),
                Button('Search Title', compact=True, id='search_title_id'),
                Button('OK', compact=True, id='ok_id')
            )
        )

    def on_mount(self) -> None:
        text_area = self.query_one('#file_path_id', TextArea)
        text_area.can_focus = False
        text_area = self.query_one('#plot_id', TextArea)
        text_area.can_focus = False

    def action_cancel_menu(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, '#fetch_details_id')
    def fetch_details_button_pressed(self, event: Button.Pressed) -> None:
        def _video_content_fetch_complete_callback(worker_state: WorkerState) -> None:
            if worker_state == WorkerState.SUCCESS:
                text_area: TextArea = self.query_one('#plot_id', TextArea)
                text_area.text = self.video_file.imdb_plot

        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed; showing VideoFetchContentModal'))
        self.app.push_screen(VideoFetchContentModal(self.video_file), _video_content_fetch_complete_callback)

    @on(Button.Pressed, '#search_title_id')
    def search_title_button_pressed(self, event: Button.Pressed) -> None:
        def _imdb_search_complete_callback(imdb_info_list: list[IMDBInfo] | None) -> None:
            if imdb_info_list is not None:
                self.post_message(LogMessage(f'[ShowMovieDetailsModal] results of VideoTitleSearchModal:'))
                for imdb_info in imdb_info_list:
                    self.post_message(LogMessage(f'[ShowMovieDetailsModal] {imdb_info.imdb_tt} {imdb_info.imdb_name} {imdb_info.imdb_year}'))

        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed; showing VideoTitleSearchModal'))
        self.app.push_screen(VideoSearchTitleModal(self.video_file), _imdb_search_complete_callback)

    @on(Button.Pressed, '#ok_id')
    def cancel_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed'))
        self.dismiss(WorkerState.SUCCESS)
