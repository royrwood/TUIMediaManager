from pathlib import Path
import dataclasses
import json

from textual_fspicker import SelectDirectory, FileOpen, FileSave

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import DataTable, Footer

from tui_media_manager.imdb.utils import VideoFile
from tui_media_manager.messages import LogMessage
from tui_media_manager.modals.show_movie_details import ShowMovieDetailsModal
from tui_media_manager.modals.video_file_scanner import VideoFileScannerModal
from tui_media_manager.modals.get_sort_by_option import ChooseSortByOptionModal


class VideoListScreen(Screen):
    BINDINGS = [('s', 'sort_video_list', 'Sort List'), ]

    def __init__(self) -> None:
        super().__init__()
        self.video_files: dict[str, VideoFile] = dict()

    def compose(self) -> ComposeResult:
        yield DataTable(show_header=True, cell_padding=2, header_height=1, cursor_type='row', id='video_files')
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns('IMDB', 'Name', 'Year', 'File')

    def load_video_files(self):
        def _file_open_result(file_path: Path | None) -> Path | None:
            self.post_message(LogMessage(f'[VideoListScreen] Selected Load File: {file_path}'))
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as file:
                    video_files_json = json.load(file)
                self.video_files = dict()
                for video_file_dict in video_files_json:
                    video_file_path = video_file_dict['file_path']
                    self.video_files[video_file_path] = VideoFile(**video_file_dict)
                self.set_video_data(self.video_files)

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
                self.app.push_screen(VideoFileScannerModal(directory_path, add_video_file_cb=self.add_video_file))

        self.app.push_screen(SelectDirectory(), _pick_directory_result)

    def set_video_data(self, video_files: dict[str, VideoFile]) -> None:
        self.video_files = video_files
        data_table = self.query_one(DataTable)
        data_table.clear()
        for video_file in video_files.values():
            video_filename = Path(video_file.file_path).name
            data_table.add_row(video_file.imdb_tt, video_file.imdb_name, video_file.imdb_year, video_filename, key=video_file.file_path)

    def add_video_file(self, video_file: VideoFile):
        if video_file.file_path not in self.video_files:
            self.video_files[video_file.file_path] = video_file

            data_table = self.query_one(DataTable)
            video_filename = Path(video_file.file_path).name
            data_table.add_row(video_file.imdb_tt, video_file.imdb_name, video_file.imdb_year, video_filename, key=video_file.file_path)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.post_message(LogMessage(f'[VideoListScreen] DataTable row selected: cursor_row={event.cursor_row}, key={event.row_key}'))
        table = self.query_one(DataTable)
        row_data = table.get_row_at(event.cursor_row)
        self.post_message(LogMessage(f'[VideoListScreen] DataTable row data by index: {row_data}'))
        row_data = table.get_row(event.row_key)
        self.post_message(LogMessage(f'[VideoListScreen] DataTable row data by key: {row_data}'))

        file_path = event.row_key.value
        video_file = self.video_files[file_path]
        # self.post_message(ShowMovieDetailsMessage(video_file))

        self.app.push_screen(ShowMovieDetailsModal(video_file))

    def action_sort_video_list(self):
        def _get_sort_option_result(sort_by_option: ChooseSortByOptionModal.SortByOptions | None) -> Path | None:
            self.post_message(LogMessage(f'[VideoListScreen] Chose sort option: {sort_by_option.name} {sort_by_option.value}'))
            if sort_by_option:
                pass

        self.app.push_screen(ChooseSortByOptionModal(), _get_sort_option_result)
