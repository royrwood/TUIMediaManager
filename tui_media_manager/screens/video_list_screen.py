from enum import StrEnum
from pathlib import Path
import copy
import dataclasses
import json
import math

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


def format_bytes(size_bytes):
    if not size_bytes:
        return "0"
    size_unit = ("B", "KB", "MB", "GB")
    size_unit_index = int(math.floor(math.log(size_bytes, 1024)))
    size_unit_str = size_unit[size_unit_index] if size_unit_index < len(size_unit) else "??"
    p = math.pow(1024, size_unit_index)
    s = round(size_bytes / p, 1)
    return f'{s}{size_unit_str}'


class VideoListScreen(Screen):
    class SortByOptions(StrEnum):
        SORT_BY_NAME_ASCENDING = 'Sort by IMDB Name Ascending'
        SORT_BY_NAME_DESCENDING = 'Sort by IMDB Name Descending'
        SORT_BY_FILEPATH_ASCENDING = 'Sort by File Name Ascending'
        SORT_BY_FILEPATH_DESCENDING = 'Sort by File Name Descending'
        SORT_BY_IMDB_TT_ASCENDING = 'Sort by IMDB Number Ascending'
        SORT_BY_IMDB_TT_DESCENDING = 'Sort by IMDB Number Descending'
        SORT_BY_IMDB_RATING_ASCENDING = 'Sort by IMDB Rating Ascending'
        SORT_BY_IMDB_RATING_DESCENDING = 'Sort by IMDB Rating Descending'
        SORT_BY_IMDB_YEAR_ASCENDING = 'Sort by IMDB Year Ascending'
        SORT_BY_IMDB_YEAR_DESCENDING = 'Sort by IMDB Year Descending'

    BINDINGS = [('s', 'sort_video_list', 'Sort List'),
                ("delete", "delete_row", "Delete Row")]

    def __init__(self) -> None:
        super().__init__()
        self.video_files: dict[str, VideoFile] = dict()
        self.sort_by = self.SortByOptions.SORT_BY_NAME_ASCENDING
        self.data_table: DataTable = DataTable(show_header=True, cell_padding=0, header_height=1, cursor_type='row', id='video_files')
        self.imdb_tt_column_key = None
        self.imdb_name_column_key = None
        self.imdb_year_column_key = None
        self.imdb_rating_column_key = None
        self.imdb_resolution_column_key = None
        self.filepath_column_key = None

    def compose(self) -> ComposeResult:
        yield self.data_table
        yield Footer()

    def on_mount(self) -> None:
        self.imdb_tt_column_key = self.data_table.add_column('IMDB Number  ')
        self.data_table.add_column(' ')
        self.imdb_name_column_key = self.data_table.add_column('[reverse]IMDB Name \u2191 [/reverse]')
        self.data_table.add_column(' ')
        self.imdb_year_column_key = self.data_table.add_column('Year  ')
        self.data_table.add_column(' ')
        self.imdb_rating_column_key = self.data_table.add_column('Rating  ')
        self.data_table.add_column(' ')
        self.imdb_resolution_column_key = self.data_table.add_column('Resolution')
        self.data_table.add_column(' ')
        self.imdb_resolution_column_key = self.data_table.add_column('Size')
        self.data_table.add_column(' ')
        self.filepath_column_key = self.data_table.add_column('Name  ')

    def add_video_file(self, video_file: VideoFile):
        if video_file.file_path not in self.video_files:
            self.video_files[video_file.file_path] = video_file
            video_filename = Path(video_file.file_path).name
            video_resolution = str(video_file.file_resolution) if video_file.file_resolution else ''
            if not video_file.file_size:
                video_file_size = '0'
            elif video_file.file_size < 1024*1024:
                s = int(video_file.file_size / 1024)
                video_file_size = f'{s}KB'
            elif video_file.file_size < 1024*1024*1024:
                s = int(video_file.file_size / (1024*1024))
                video_file_size = f'{s}MB'
            else:
                s = round(video_file.file_size / (1024*1024*1024), 1)
                video_file_size = f'{s}GB'

            # TODO: Sorting without horrible performance hit....?
            self.data_table.add_row(video_file.imdb_tt, '', video_file.imdb_name, '', video_file.imdb_year, '', video_file.imdb_rating, '', video_resolution, '', video_file_size, '', video_filename, key=video_file.file_path)

    def load_video_files(self):
        def _file_open_result(file_path: Path | None) -> Path | None:
            self.post_message(LogMessage(f'[VideoListScreen] Selected Load File: {file_path}'))
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as file:
                    video_files_json = json.load(file)
                self.video_files = dict()
                for video_file_dict in video_files_json:
                    self.add_video_file(VideoFile(**video_file_dict))
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
                self.start_scanning_directory(directory_path, do_full_imdb_fetch=True)
            elif button_choice == 'Brief':
                self.start_scanning_directory(directory_path, do_full_imdb_fetch=False)
            else:
                self.post_message(LogMessage(f'[VideoListScreen] User cancelled scanning option dialog'))

        self.app.push_screen(ButtonChoicesModal('Get full or brief IMDB info?', ['Full', 'Brief']), _button_choice_modal_callback)

    def start_scanning_directory(self, directory_path: Path, do_full_imdb_fetch: bool) -> None:
        def _scanning_complete_callback(_scan_result: bool) -> None:
            self.post_message(LogMessage(f'[VideoListScreen] Scanning complete for directory "{directory_path}"'))
            self.sort_table()

        self.app.push_screen(VideoFileScannerModal(directory_path, add_video_file_cb=self.add_video_file, do_full_imdb_fetch=do_full_imdb_fetch), _scanning_complete_callback)

    def sort_table(self) -> None:
        self.data_table.columns[self.imdb_tt_column_key].label = 'IMDB Number  '
        self.data_table.columns[self.imdb_name_column_key].label = 'IMDB Name  '
        self.data_table.columns[self.imdb_year_column_key].label = 'Year  '
        self.data_table.columns[self.imdb_rating_column_key].label = 'Rating  '
        self.data_table.columns[self.filepath_column_key].label = 'File Name  '

        if self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_TT_ASCENDING:
            self.data_table.columns[self.imdb_tt_column_key].label = '[reverse]IMDB Number \u2191[/reverse]'
            self.data_table.sort(key=lambda row: row[0].lower())
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_TT_DESCENDING:
            self.data_table.columns[self.imdb_tt_column_key].label = '[reverse]IMDB Number \u2193[/reverse]'
            self.data_table.sort(key=lambda row: row[0].lower(), reverse=True)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_NAME_ASCENDING:
            self.data_table.columns[self.imdb_name_column_key].label = '[reverse]IMDB Name \u2191[/reverse]'
            self.data_table.sort(key=lambda row: row[2].lower())
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_NAME_DESCENDING:
            self.data_table.columns[self.imdb_name_column_key].label = '[reverse]IMDB Name \u2193[/reverse]'
            self.data_table.sort(key=lambda row: row[2].lower(), reverse=True)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_YEAR_ASCENDING:
            self.data_table.columns[self.imdb_year_column_key].label = '[reverse]Year \u2191[/reverse]'
            self.data_table.sort(key=lambda row: int(row[4]) if row[4] else 0)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_YEAR_DESCENDING:
            self.data_table.columns[self.imdb_year_column_key].label = '[reverse]Year \u2193[/reverse]'
            self.data_table.sort(key=lambda row: int(row[4]) if row[4] else 0, reverse=True)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_ASCENDING:
            self.data_table.columns[self.imdb_rating_column_key].label = '[reverse]Rating \u2191[/reverse]'
            self.data_table.sort(key=lambda row: float(row[6]) if row[6] else 0.0)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_DESCENDING:
            self.data_table.columns[self.imdb_rating_column_key].label = '[reverse]Rating \u2193[/reverse]'
            self.data_table.sort(key=lambda row: float(row[6]) if row[6] else 0.0, reverse=True)
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_FILEPATH_ASCENDING:
            self.data_table.columns[self.filepath_column_key].label = '[reverse]File Name \u2191 [/reverse]'
            self.data_table.sort(key=lambda row: row[12].lower())
        elif self.sort_by == VideoListScreen.SortByOptions.SORT_BY_FILEPATH_DESCENDING:
            self.data_table.columns[self.filepath_column_key].label = '[reverse]File Name \u2193[/reverse]'
            self.data_table.sort(key=lambda row: row[12].lower(), reverse=True)

        self.data_table.refresh()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        def _movie_details_callback(_video_file: VideoFile) -> None:
            if _video_file:
                self.post_message(LogMessage(f'[VideoListScreen] VideoFile was updated'))

        self.post_message(LogMessage(f'[VideoListScreen] DataTable row selected: cursor_row={event.cursor_row}, key={event.row_key}'))
        row_data = self.data_table.get_row_at(event.cursor_row)
        self.post_message(LogMessage(f'[VideoListScreen] DataTable row data by index: {row_data}'))
        row_data = self.data_table.get_row(event.row_key)
        self.post_message(LogMessage(f'[VideoListScreen] DataTable row data by key: {row_data}'))

        file_path = event.row_key.value
        video_file = self.video_files[file_path]

        self.app.push_screen(ShowMovieDetailsModal(copy.deepcopy(video_file)), _movie_details_callback)

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
        elif column_key == self.imdb_year_column_key:
            self.sort_by = VideoListScreen.SortByOptions.SORT_BY_IMDB_YEAR_DESCENDING if prev_sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_YEAR_ASCENDING else VideoListScreen.SortByOptions.SORT_BY_IMDB_YEAR_ASCENDING
        elif column_key == self.imdb_rating_column_key:
            self.sort_by = VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_DESCENDING if prev_sort_by == VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_ASCENDING else VideoListScreen.SortByOptions.SORT_BY_IMDB_RATING_ASCENDING
        elif column_key == self.filepath_column_key:
            self.sort_by = VideoListScreen.SortByOptions.SORT_BY_FILEPATH_DESCENDING if prev_sort_by == VideoListScreen.SortByOptions.SORT_BY_FILEPATH_ASCENDING else VideoListScreen.SortByOptions.SORT_BY_FILEPATH_ASCENDING

        if self.sort_by != prev_sort_by:
            self.sort_table()

    def action_delete_row(self) -> None:
        row_key, column_key = self.data_table.coordinate_to_cell_key(self.data_table.cursor_coordinate)
        self.post_message(LogMessage(f'[VideoListScreen] Deleting row: row_key={row_key}'))
        # self.remove_row(row_key)
