from collections.abc import Callable
from pathlib import Path
import os
import asyncio

from textual import on
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal
from textual.worker import WorkerState

from tui_media_manager.imdb.utils import VideoFile
from tui_media_manager.messages import LogMessage
from tui_media_manager.imdb.utils import scrub_video_file_name, get_imdb_basic_info


class VideoFileScannerModal(ModalScreen):
    CSS = """
        VideoFileScannerModal {
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

    def __init__(self, directory_path: Path, add_video_file_cb: Callable[[VideoFile], None]):
        super().__init__()
        self.directory_path = directory_path
        self.directory_scan_worker = None
        self.add_video_file_cb = add_video_file_cb

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(f'Scanning items in directory {self.directory_path}', id='message_id'),
            Horizontal(
                Button('Cancel', compact=True, id='cancel_id')
            )
        )

    def on_mount(self) -> None:
        def _log_message(message: str) -> None:
            self.post_message(LogMessage(message))

        def _scanning_complete() -> None:
            self.post_message(LogMessage(f'Directory scanning complete; dismissing VideoFileScannerModal'))
            self.dismiss()

        def _add_video_file(video_file: VideoFile) -> None:
            if self.add_video_file_cb:
                self.add_video_file_cb(video_file)

        self.post_message(LogMessage(f'Starting worker to scan directory {self.directory_path}...'))
        self.directory_scan_worker = self.run_worker(self.scan_folder(self.directory_path, _log_message, _scanning_complete, _add_video_file))
        self.post_message(LogMessage(f'Started worker to scan directory {self.directory_path}'))

    @on(Button.Pressed, '#cancel_id')
    def on_button_pressed(self, _event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'VideoFileScannerModal "Cancel" Button pressed'))

        if self.directory_scan_worker and self.directory_scan_worker.state == WorkerState.RUNNING:
            self.post_message(LogMessage(f'VideoFileScannerModal cancelling worker...'))
            self.directory_scan_worker.cancel()
            self.post_message(LogMessage(f'VideoFileScannerModal worker cancelled'))

        # I don't think we need to dismiss, since canceling the worker will trigger a call to _scanning_complete(), and that calls self.dismiss()
        # self.dismiss()

    async def scan_folder(self,
                          folder_path: Path,
                          log_message_cb: Callable[[str], None],
                          scanning_complete_cb: Callable[[], None],
                          add_video_file_cb: Callable[[VideoFile], None],
                          include_extensions: str = None) -> None:
        try:
            if include_extensions is None:
                include_extensions = 'mkv,mp4'

            include_extensions_list = [ext.lower().strip() for ext in include_extensions.split(',')]

            log_message_cb(f'Beginning processing of directory: {str(folder_path)}')

            for dir_path, dirs, files in os.walk(folder_path):
                for filename in files:
                    file_path = os.path.join(dir_path, filename)
                    filename_parts = os.path.splitext(filename)
                    filename_no_extension = filename_parts[0]
                    filename_extension = filename_parts[1]
                    if filename_extension.startswith('.'):
                        filename_extension = filename_extension[1:]

                    if filename_extension.lower() not in include_extensions_list:
                        log_message_cb(f'Ignoring file: {file_path}')
                        continue

                    scrubbed_video_file_name, year = scrub_video_file_name(filename_no_extension)
                    video_file = VideoFile(file_path=file_path, scrubbed_file_name=scrubbed_video_file_name, scrubbed_file_year=year)

                    log_message_cb(f'Getting IMDB info for video file: {file_path}')
                    imdb_info_list = await get_imdb_basic_info(video_file.scrubbed_file_name, video_file.scrubbed_file_year, num_matches=1)
                    imdb_info = imdb_info_list[0]
                    if imdb_info:
                        log_message_cb(f'Found: tt={imdb_info.imdb_tt}, name={imdb_info.imdb_name}, year={imdb_info.imdb_year}')
                        video_file.imdb_tt = imdb_info.imdb_tt
                        video_file.imdb_name = imdb_info.imdb_name
                        video_file.imdb_year = imdb_info.imdb_year
                        video_file.imdb_rating = imdb_info.imdb_rating
                        video_file.imdb_plot = imdb_info.imdb_plot
                        video_file.imdb_plot = 'This is the plot\n\nMore plot details\n\nThe End.'
                        video_file.imdb_genres = imdb_info.imdb_genres

                        log_message_cb(f'Processed video file: {file_path}')
                        add_video_file_cb(video_file)

            log_message_cb(f'End processing of directory: {str(folder_path)}')
            scanning_complete_cb()

        except asyncio.CancelledError:
            log_message_cb(f'Caught CancelledError while processing directory: {str(folder_path)}')
            scanning_complete_cb()
