from enum import StrEnum
from pathlib import Path
import dataclasses
import json

from textual_fspicker import SelectDirectory, FileOpen, FileSave

from textual import on
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import DataTable, Footer

from tui_media_manager.imdb.utils import VideoFile
from tui_media_manager.messages import LogMessage
from tui_media_manager.modals.show_movie_details import ShowMovieDetailsModal
from tui_media_manager.modals.video_file_scanner import VideoFileScannerModal
from tui_media_manager.modals.popup_menu import PopupMenuModal
from tui_media_manager.modals.button_choices import ButtonChoicesModal


class VideoListScreen(Screen):
    class SortByOptions(StrEnum):
        SORT_BY_NAME_ASCENDING = 'Sort by IMDB Name Ascending'
        SORT_BY_NAME_DESCENDING = 'Sort by IMDB Name Descending'
        SORT_BY_FILEPATH_ASCENDING = 'Sort by File Path Ascending'
        SORT_BY_FILEPATH_DESCENDING = 'Sort by File Path Descending'
        SORT_BY_IMDB_TT_ASCENDING = 'Sort by IMDB Number Ascending'
        SORT_BY_IMDB_TT_DESCENDING = 'Sort by IMDB Number Descending'
        SORT_BY_IMDB_RATING_ASCENDING = 'Sort by IMDB Rating Ascending'
        SORT_BY_IMDB_RATING_DESCENDING = 'Sort by IMDB Rating Descending'

    BINDINGS = [('s', 'sort_video_list', 'Sort List'), ]

    def __init__(self) -> None:
        super().__init__()
        self.video_files: dict[str, VideoFile] = dict()
        self.sort_by = self.SortByOptions.SORT_BY_NAME_ASCENDING
        self.data_table: DataTable = DataTable(show_header=True, cell_padding=2, header_height=1, cursor_type='row', id='video_files')
        self.imdb_tt_column_key = None
        self.imdb_name_column_key = None
        self.imdb_year_column_key = None
        self.imdb_rating_column_key = None
        self.filepath_column_key = None

    def compose(self) -> ComposeResult:
        yield self.data_table
        yield Footer()

    def on_mount(self) -> None:
        self.imdb_tt_column_key = self.data_table.add_column(' IMDB Number  ')
        self.imdb_name_column_key = self.data_table.add_column(' IMDB Name  ')
        self.imdb_year_column_key = self.data_table.add_column(' Year  ')
        self.imdb_rating_column_key = self.data_table.add_column(' Rating  ')
        self.filepath_column_key = self.data_table.add_column('[reverse] File Path  [/reverse]')

    def load_video_files(self):
        def _file_open_result(file_path: Path | None) -> Path | None:
            self.post_message(LogMessage(f'[VideoListScreen] Selected Load File: {file_path}'))
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as file:
                    video_files_json = json.load(file)
                self.video_files = dict()
                for video_file_dict in video_files_json:
                    video_file_path = video_file_dict['file_path']
                    video_file = VideoFile(**video_file_dict)
                    video_filename = Path(video_file.file_path).name
                    self.video_files[video_file_path] = video_file
                    self.data_table.add_row(video_file.imdb_tt, video_file.imdb_name, video_file.imdb_year, video_file.imdb_rating, video_filename, key=video_file.file_path)
                self.sort_table()

        self.app.push_screen(FileOpen(), _file_open_result)

    def save_video_files(self):
        def _file_save_result(file_path: Path | None) -> Path | None:
            self.post_message(LogMessage(f'[VideoListScreen] Selected Save File: {file_path}'))
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write('[\n')
                    for i, video_file in enumerate(self.video_files.values()):
                        if i > 0:
                            file.write(',\n')
                        video_file_json = '  ' + json.dumps(dataclasses.asdict(video_file), ensure_ascii=False)
                        file.write(video_file_json)
                    file.write('\n]\n')

        self.app.push_screen(FileSave(), _file_save_result)

    def pick_a_directory_and_start_scanning(self) -> None:
        def _pick_directory_result(directory_path: Path | None) -> Path | None:
            self.post_message(LogMessage(f'[VideoListScreen] Selected directory: {directory_path}'))
            if directory_path:
                self.get_scan_options_and_start_scanning(directory_path)

        self.app.push_screen(SelectDirectory(), _pick_directory_result)

    def get_scan_options_and_start_scanning(self, directory_path: Path) -> None:
        def _button_choice_modal_callback(button_choice: str | None) -> None:
            self.post_message(LogMessage(f'[VideoListScreen] Got button_choice="{button_choice}"'))
            if button_choice == 'Full':
                self.app.push_screen(VideoFileScannerModal(directory_path, add_video_file_cb=self.add_video_file, do_full_imdb_fetch=True))
            elif button_choice == 'Brief':
                self.app.push_screen(VideoFileScannerModal(directory_path, add_video_file_cb=self.add_video_file, do_full_imdb_fetch=False))

        self.app.push_screen(ButtonChoicesModal('Get full or brief IMDB info?', ['Full', 'Brief']), _button_choice_modal_callback)

    def sort_table(self) -> None:
        self.data_table.columns[self.imdb_tt_column_key].label = 'IMDB Number  '
        self.data_table.columns[self.imdb_name_column_key].label = 'IMDB Name  '
        self.data_table.columns[self.imdb_year_column_key].label = 'Year  '
        self.data_table.columns[self.imdb_rating_column_key].label = 'Rating  '
        self.data_table.columns[self.filepath_column_key].label = 'File Path  '

        if self.sort_by == VideoListScreen.SortByOptions.SORT_BY_FILEPATH_ASCENDING:
            self.data_table.columns[self.filepath_column_key].label = '[reverse] File Path \u2193 [/reverse]'
            self.data_table.sort(key=lambda row: row[4].lower())
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_FILEPATH_DESCENDING:
            self.data_table.columns[self.filepath_column_key].label = '[reverse] File Path \u2193[/reverse]'
            self.data_table.sort(key=lambda row: row[4].lower(), reverse=True)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_TT_ASCENDING:
            self.data_table.columns[self.imdb_tt_column_key].label = '[reverse] IMDB Number \u2193[/reverse]'
            self.data_table.sort(key=lambda row: row[0].lower())
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_TT_DESCENDING:
            self.data_table.columns[self.imdb_tt_column_key].label = '[reverse] IMDB Number \u2193[/reverse]'
            self.data_table.sort(key=lambda row: row[0].lower(), reverse=True)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_ASCENDING:
            self.data_table.columns[self.imdb_rating_column_key].label = '[reverse] Rating \u2193[/reverse]'
            self.data_table.sort(key=lambda row: float(row[3]) if row[3] else 0.0)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_DESCENDING:
            self.data_table.columns[self.imdb_rating_column_key].label = '[reverse] Rating \u2193[/reverse]'
            self.data_table.sort(key=lambda row: float(row[3]) if row[3] else 0.0, reverse=True)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_NAME_ASCENDING:
            self.data_table.columns[self.imdb_name_column_key].label = '[reverse] IMDB Name \u2193[/reverse]'
            self.data_table.sort(key=lambda row: row[4].lower())
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_NAME_DESCENDING:
            self.data_table.columns[self.imdb_name_column_key].label = '[reverse] IMDB Name \u2193[/reverse]'
            self.data_table.sort(key=lambda row: row[4].lower(), reverse=True)

        self.data_table.refresh()

    def add_video_file(self, video_file: VideoFile):
        if video_file.file_path not in self.video_files:
            self.video_files[video_file.file_path] = video_file

            video_filename = Path(video_file.file_path).name
            self.data_table.add_row(video_file.imdb_tt, video_file.imdb_name, video_file.imdb_year, video_file.imdb_rating, video_filename, key=video_file.file_path)

            # TODO: Sorting without horrible performance hit....?

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.post_message(LogMessage(f'[VideoListScreen] DataTable row selected: cursor_row={event.cursor_row}, key={event.row_key}'))
        row_data = self.data_table.get_row_at(event.cursor_row)
        self.post_message(LogMessage(f'[VideoListScreen] DataTable row data by index: {row_data}'))
        row_data = self.data_table.get_row(event.row_key)
        self.post_message(LogMessage(f'[VideoListScreen] DataTable row data by key: {row_data}'))

        file_path = event.row_key.value
        video_file = self.video_files[file_path]

        self.app.push_screen(ShowMovieDetailsModal(video_file))

    def action_sort_video_list(self):
        def _get_sort_option_result(sort_by_option: VideoListScreen.SortByOptions | None) -> Path | None:
            self.post_message(LogMessage(f'[VideoListScreen] Chose sort option: {sort_by_option.name} {sort_by_option.value}'))
            if sort_by_option:
                self.sort_by = sort_by_option
                self.sort_table()

        self.app.push_screen(PopupMenuModal(VideoListScreen.SortByOptions), _get_sort_option_result)

    @on(DataTable.HeaderSelected)
    def on_header_clicked(self, event: DataTable.HeaderSelected) -> None:
        column_key = event.column_key

        prev_sort_by = self.sort_by

        if column_key == self.imdb_tt_column_key:
            self.sort_by = VideoListScreen.SortByOptions.SORT_BY_IMDB_TT_DESCENDING if prev_sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_TT_ASCENDING else VideoListScreen.SortByOptions.SORT_BY_IMDB_TT_ASCENDING
        elif column_key == self.imdb_name_column_key:
            self.sort_by = VideoListScreen.SortByOptions.SORT_BY_NAME_DESCENDING if prev_sort_by == VideoListScreen.SortByOptions.SORT_BY_NAME_ASCENDING else VideoListScreen.SortByOptions.SORT_BY_NAME_ASCENDING
        elif column_key == self.imdb_rating_column_key:
            self.sort_by = VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_DESCENDING if prev_sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_ASCENDING else VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_ASCENDING
        elif column_key == self.filepath_column_key:
            self.sort_by = VideoListScreen.SortByOptions.SORT_BY_FILEPATH_DESCENDING if prev_sort_by == VideoListScreen.SortByOptions.SORT_BY_FILEPATH_ASCENDING else VideoListScreen.SortByOptions.SORT_BY_FILEPATH_ASCENDING

        if self.sort_by != prev_sort_by:
            self.sort_table()
