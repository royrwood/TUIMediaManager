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
from tui_media_manager.imdb.utils import scrub_video_file_name, get_imdb_basic_info, get_imdb_details


class VideoFileScannerModal(ModalScreen):
    CSS = """
        VideoFileScannerModal {
            align-horizontal: center;
            
            & > Vertical {
                width: 75vw;
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
            Label(f'Scanning items in directory {self.directory_path}...', id='message_id'),
            Label(f'', id='file_id'),
            Label(f'', id='progress_id'),
            Horizontal(
                Button('Cancel', compact=True, id='cancel_id')
            )
        )

    def on_mount(self) -> None:
        def _log_message(message: str) -> None:
            self.post_message(LogMessage(message))

        def _progress_update(progress_info: dict[str, str]) -> None:
            # self.post_message(LogMessage(f'[VideoFileScannerModal] {message}'))
            label: Label = self.query_one('#file_id', Label)
            label.update(f'Current file: {progress_info["filename"]}')
            label: Label = self.query_one('#progress_id', Label)
            label.update(progress_info['progress'])

        def _scanning_complete() -> None:
            self.post_message(LogMessage(f'[VideoFileScannerModal] Directory scanning complete; dismissing VideoFileScannerModal'))
            self.dismiss()

        self.post_message(LogMessage(f'[VideoFileScannerModal] Starting worker to scan directory {self.directory_path}...'))
        self.directory_scan_worker = self.run_worker(self.scan_folder(self.directory_path, _progress_update, _scanning_complete, self.add_video_file_cb))
        self.post_message(LogMessage(f'[VideoFileScannerModal] Started worker to scan directory {self.directory_path}'))

    @on(Button.Pressed, '#cancel_id')
    def on_button_pressed(self, _event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[VideoFileScannerModal] "Cancel" Button pressed'))

        if self.directory_scan_worker and self.directory_scan_worker.state == WorkerState.RUNNING:
            self.post_message(LogMessage(f'[VideoFileScannerModal] cancelling worker...'))
            self.directory_scan_worker.cancel()
            self.post_message(LogMessage(f'[VideoFileScannerModal] worker cancelled'))

        # I don't think we need to dismiss, since canceling the worker will trigger a call to _scanning_complete(), and that calls self.dismiss()
        # self.dismiss()

    async def scan_folder(self,
                          folder_path: Path,
                          progress_update_cb: Callable[[dict], None],
                          scanning_complete_cb: Callable[[], None],
                          add_video_file_cb: Callable[[VideoFile], None],
                          include_extensions: str = None) -> None:
        try:
            if include_extensions is None:
                include_extensions = 'mkv,mp4'

            include_extensions_list = [ext.lower().strip() for ext in include_extensions.split(',')]

            progress_update_cb({'filename': str(folder_path), 'progress': 'Begin processing directory...'})

            for dir_path, dirs, files in os.walk(folder_path):
                for filename in files:
                    file_path = os.path.join(dir_path, filename)
                    filename_parts = os.path.splitext(filename)
                    filename_no_extension = filename_parts[0]
                    filename_extension = filename_parts[1]
                    if filename_extension.startswith('.'):
                        filename_extension = filename_extension[1:]

                    if filename_extension.lower() not in include_extensions_list:
                        progress_update_cb({'filename': filename, 'progress': 'Skipping file'})
                        continue

                    scrubbed_video_file_name, scrubbed_year = scrub_video_file_name(filename_no_extension)

                    progress_update_cb({'filename': filename, 'progress': 'Finding basic IMDB info...'})
                    imdb_info_list = await get_imdb_basic_info(scrubbed_video_file_name, scrubbed_year, num_matches=1)
                    imdb_basic_info = imdb_info_list[0]
                    if imdb_basic_info:
                        progress_update_cb({'filename': filename, 'progress': 'Found basic IMDB info'})

                        progress_update_cb({'filename': filename, 'progress': 'Finding detailed IMDB info...'})
                        imdb_full_info = await get_imdb_details(imdb_basic_info.imdb_tt)
                        progress_update_cb({'filename': filename, 'progress': 'Found detailed IMDB info'})

                        video_file = VideoFile(file_path=file_path,
                                               scrubbed_file_name=scrubbed_video_file_name,
                                               scrubbed_file_year=scrubbed_year,
                                               imdb_tt=imdb_full_info.imdb_tt,
                                               imdb_name=imdb_full_info.imdb_name,
                                               imdb_year=imdb_full_info.imdb_year,
                                               imdb_rating=imdb_full_info.imdb_rating,
                                               imdb_plot=imdb_full_info.imdb_plot,
                                               imdb_genres=imdb_full_info.imdb_genres)
                        add_video_file_cb(video_file)

            progress_update_cb({'filename': str(folder_path), 'progress': 'End processing directory'})
            scanning_complete_cb()

        except asyncio.CancelledError:
            progress_update_cb({'filename': str(folder_path), 'progress': 'Processing interrupted by asyncio.CancelledError'})
            scanning_complete_cb()
