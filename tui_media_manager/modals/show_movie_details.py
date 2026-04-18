from textual import on
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import TextArea, Button
from textual.containers import Vertical, Horizontal
from textual.worker import WorkerState

from tui_media_manager.imdb.utils import VideoFile, IMDBInfo
from tui_media_manager.messages import LogMessage
from tui_media_manager.modals.get_search_title import GetSearchTitleModal
from tui_media_manager.modals.search_imdb_by_title import SearchIMDBByTitleModal
from tui_media_manager.modals.review_imdb_search_results import ReviewIMDBSearchResultsModal


class ShowMovieDetailsModal(ModalScreen):
    CSS = """
        ShowMovieDetailsModal {
            align: center middle;
        
            & > Vertical {
                min-width: 60vw;
                width: auto;
                height: auto;
                keyline: thin $primary;
        
                & > #file_path_id {
                    width: 100%;
                    height: auto;
                    margin: 1;
                }
        
                & > #plot_id {
                    width: 100%;
                    height: auto;
                    margin: 1;
                    padding: 1 2 1 2;
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
    AUTO_FOCUS = "#ok_id"

    def __init__(self, video_file: VideoFile):
        super().__init__()
        self.video_file = video_file
        self.imdb_worker = None
        self.file_text_area = TextArea(self.video_file.file_path, read_only=True, show_cursor=False, id='file_path_id')
        self.file_text_area.can_focus = False
        self.plot_text_area = TextArea(self.video_file.imdb_plot, read_only=True, show_cursor=False, id='plot_id')
        self.plot_text_area.can_focus = False
        self.search_imdb_button = Button('Search IMDB', compact=True, id='search_imdb_id')
        self.ok_button = Button('OK', compact=True, id='ok_id')

        if self.video_file.imdb_plot:
            self.ok_button.focus()
        else:
            self.search_imdb_button.focus()

    def compose(self) -> ComposeResult:
        yield Vertical(
            self.file_text_area,
            self.plot_text_area,
            Horizontal(
                self.search_imdb_button,
                self.ok_button
            )
        )

    # def on_mount(self) -> None:
    #     if self.video_file.imdb_plot:
    #         button = self.query_one('#ok_id', Button)
    #         button.focus()
    #     else:
    #         button = self.query_one('#search_imdb_id', Button)
    #         button.focus()

    def action_do_cancel(self) -> None:
        self.dismiss(None)

    def get_search_query_params(self):
        def _video_search_query_params_callback(search_title: str) -> None:
            if search_title is not None:
                self.post_message(LogMessage(f'[ShowMovieDetailsModal] GetSearchTitleModal returned "{search_title}"'))
                self.search_imdb_for_title(search_title)

        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Showing GetSearchTitleModal'))
        self.app.push_screen(GetSearchTitleModal(self.video_file), _video_search_query_params_callback)

    def search_imdb_for_title(self, search_title: str):
        def _video_search_title_callback(imdb_info_list: list[IMDBInfo]) -> None:
            if search_title is not None:
                self.post_message(LogMessage(f'[ShowMovieDetailsModal] SearchIMDBByTitleModal returned {len(imdb_info_list)} items:'))
                for i, imdb_info in enumerate(imdb_info_list):
                    self.post_message(LogMessage(f'[ShowMovieDetailsModal] {i:02}: {imdb_info.imdb_tt} {imdb_info.imdb_name} {imdb_info.imdb_year} '))
                self.review_imdb_search_results(imdb_info_list)

        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Showing SearchIMDBByTitleModal'))
        self.app.push_screen(SearchIMDBByTitleModal(search_title), _video_search_title_callback)

    def review_imdb_search_results(self, imdb_info_list: list[IMDBInfo]):
        def _review_search_results_callback(imdb_info: IMDBInfo) -> None:
            if imdb_info is not None:
                self.post_message(LogMessage(f'[ShowMovieDetailsModal] Updating current VideoFile with returned IMDB data: {imdb_info}'))
                self.video_file.imdb_tt = imdb_info.imdb_tt
                self.video_file.imdb_name = imdb_info.imdb_name
                self.video_file.imdb_year = imdb_info.imdb_year
                self.video_file.imdb_rating = imdb_info.imdb_rating
                self.video_file.imdb_genres = imdb_info.imdb_genres
                self.video_file.imdb_plot = imdb_info.imdb_plot
                self.plot_text_area.text = self.video_file.imdb_plot or ''
                self.ok_button.focus()

        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Showing ReviewIMDBSearchResultsModal'))
        self.app.push_screen(ReviewIMDBSearchResultsModal(imdb_info_list), _review_search_results_callback)

    @on(Button.Pressed, '#search_imdb_id')
    def search_imdb_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed'))
        self.get_search_query_params()

    @on(Button.Pressed, '#ok_id')
    def ok_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed'))
        self.dismiss(None)
