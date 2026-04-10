from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
import asyncio
import dataclasses
import json
import logging
import os
import re

from imdbinfo import search_title, get_movie
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.message import Message
from textual.screen import Screen, ModalScreen
from textual.widgets import DataTable, Label, ListItem, ListView, Log, Footer, Button, TextArea
from textual.worker import Worker, WorkerState
from textual_fspicker import SelectDirectory, FileOpen, FileSave
import aiohttp
import textual


LOGGER = logging.getLogger(__name__)
logging.basicConfig(filename='tui_media_manager.log', encoding='utf-8', level=logging.INFO)
LOGGER.info('Starting up...')


###############
# Data classes
###############

@dataclasses.dataclass
class VideoFile:
    file_path: str = ''
    scrubbed_file_name: str = ''
    scrubbed_file_year: str = ''
    imdb_tt: str = ''
    imdb_name: str = ''
    imdb_year: str = ''
    imdb_rating: str = ''
    imdb_genres: list[str] = None
    imdb_plot: str = None
    is_dirty: bool = False


@dataclasses.dataclass
class IMDBInfo:
    imdb_tt: str = ''
    imdb_name: str = ''
    imdb_year: str = ''
    imdb_rating: str = ''
    imdb_genres: list[str] = None
    imdb_plot: str = ''


##################
# Message Classes
##################

class LogMessage(Message):
    def __init__(self, message: str, level=0):
        super().__init__()
        self.message = message
        self.level = level


# class ShowMovieDetailsMessage(Message):
#     def __init__(self, video_file: VideoFile):
#         super().__init__()
#         self.video_file = video_file


class AddVideoFile(Message):
    def __init__(self, video_file: VideoFile):
        super().__init__()
        self.video_file = video_file


####################
# Utility Functions
####################

def scrub_video_file_name(file_name: str, filename_metadata_tokens: str = None) -> tuple[str, str]:
    if filename_metadata_tokens is None:
        filename_metadata_tokens = '480p,720p,1080p,bluray,hevc,x265,x264,web,webrip,web-dl,repack,proper,extended,remastered,dvdrip,dvd,hdtv,xvid,hdrip,brrip,dvdscr,pdtv'

    year = ''

    match = re.match(r'((.*)\((\d{4})\))', file_name)
    if match:
        file_name = match.group(2)
        year = match.group(3)
        scrubbed_file_name_list = file_name.replace('.', ' ').split()

    else:
        metadata_token_list = [token.lower().strip() for token in filename_metadata_tokens.split(',')]
        file_name_parts = file_name.replace('.', ' ').split()
        scrubbed_file_name_list = list()

        for file_name_part in file_name_parts:
            file_name_part = file_name_part.lower()

            if file_name_part in metadata_token_list:
                break
            scrubbed_file_name_list.append(file_name_part)

        if scrubbed_file_name_list:
            match = re.match(r'\(?(\d{4})\)?', scrubbed_file_name_list[-1])
            if match:
                year = match.group(1)
                del scrubbed_file_name_list[-1]

    scrubbed_file_name = ' '.join(scrubbed_file_name_list).strip()
    scrubbed_file_name = re.sub(' +', ' ', scrubbed_file_name)
    return scrubbed_file_name, year


async def get_imdb_basic_info(video_name: str, year: str | None, num_matches: int = 1) -> list[IMDBInfo]:
    # curl -s -H 'Content-Type: application/json' -d @imdb_graphql_simple.json 'https://api.graphql.imdb.com/'

    year = '' if year is None else year

    # This is the GraphQL-- it is not JSON!
    imdb_graphql = f"""
        query {{
          mainSearch(
            first: {num_matches}
            options: {{
              searchTerm: "{video_name} {year}"
              isExactMatch: false
              type: [TITLE]
              titleSearchOptions: {{ type: [MOVIE] }}
            }}
          ) {{
            edges {{
              node {{
                entity {{
                  ... on Title {{
                    __typename
                    id
                    titleText {{ text }}
                    canonicalUrl
                    originalTitleText {{ text }}
                    releaseDate {{ year month day }}
                    primaryImage {{ url }}
                    titleType {{ id text categories {{ id text value }} }}
                    ratingsSummary {{ aggregateRating }}
                    runtime {{ seconds }}
                  }}
                }}
              }}
            }}
          }}
        }}
    """
    # Now pack the GraphQL as a string in a JSON object
    imdb_graphql_json = {'query': imdb_graphql}
    headers = {'Content-Type': 'application/json'}
    url = 'https://api.graphql.imdb.com/'

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=imdb_graphql_json, timeout=30) as imdb_response:
            if imdb_response.status < 200 or imdb_response.status >= 300:
                raise Exception(f'HTTP {imdb_response.status} while fetching search results for {video_name}')
            else:
                imdb_response_text = await imdb_response.text()
                imdb_response_json = json.loads(imdb_response_text)
                edges = imdb_response_json['data']['mainSearch']['edges']
                imdb_info_list = list()
                for edge in edges:
                    edge_node_entity = edge['node']['entity']
                    imdb_info = IMDBInfo()
                    imdb_info.imdb_tt = edge_node_entity['id']
                    imdb_info.imdb_name = edge_node_entity['titleText']['text']
                    imdb_info.imdb_year = str(edge_node_entity['releaseDate']['year'])
                    imdb_info_list.append(imdb_info)
                return imdb_info_list


async def scan_folder(folder_path: Path,
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


async def get_imdb_details(imdb_tt: str) -> IMDBInfo:
    movie_details = await asyncio.to_thread(get_movie, imdb_tt)
    imdb_info = IMDBInfo(imdb_tt=imdb_tt,
                         imdb_name=movie_details.title_localized,
                         imdb_year=str(movie_details.year),
                         imdb_rating=str(movie_details.rating),
                         imdb_plot=movie_details.plot,
                         imdb_genres=movie_details.genres)
    return imdb_info


#################
# Screen Classes
#################

class MainMenu(ModalScreen):
    class MainMenuActions(StrEnum):
        SHOW_TABLE_SCREEN = 'Show Data Table'
        SHOW_LOG_SCREEN = 'Show Log'
        LOAD_VIDEO_LIST = 'Load Video Data'
        SAVE_VIDEO_LIST = 'Save Video Data'
        PICK_A_DIRECTORY = 'Pick a Directory'
        STOP_DIRECTORY_SCAN = 'Stop Directory Scan'

    CSS = """
         MainMenu {
             align-horizontal: center;

             & > ListView {
                 width: auto;
                 height: auto;
                 offset-y: 25vh;

                 & > ListItem {
                     width: auto;
                     min-width: 100%;
                     padding: 0 1;
                 }
             }
         }
     """

    BINDINGS = [('escape', 'cancel_menu', 'Cancel Menu')]

    def compose(self) -> ComposeResult:
        # Use a ListView so arrow keys can navigate up and down in the list
        with ListView():
            for menu_action in MainMenu.MainMenuActions:
                yield ListItem(Label(str(menu_action.value)), id=menu_action.name)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # main_menu_actions_enum = MainMenuActions[event.item.id]  # Pycharm linter complains about this because MainMenuActions is a StrEnum, not a plain Enum
        main_menu_actions_enum = getattr(MainMenu.MainMenuActions, event.item.id)  # Pycharm linter likes this way of getting the enum by name-- FINE, WHATEVER.
        self.dismiss(main_menu_actions_enum)

    def action_cancel_menu(self) -> None:
        self.dismiss(None)


class LogScreen(Screen):
    CSS = """
        Log {
            border: solid white;
            scrollbar-visibility: hidden;
        }
    """

    def __init__(self):
        super().__init__()
        self.logger = Log()

    def compose(self) -> ComposeResult:
        yield self.logger
        yield Footer()

    # def on_mount(self) -> None:
    #     self.info("Hello, World!")

    def info(self, message: str) -> None:
        LOGGER.info('[LogScreen] info: message="%s"', message)
        self.logger.write_line(message)


class TableScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.video_files: dict[str, VideoFile] = dict()

    def compose(self) -> ComposeResult:
        yield DataTable(show_header=True, cell_padding=2, header_height=1, cursor_type='row', id='video_files')
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns('IMDB', 'Name', 'Year', 'File')
        # table.add_row('', '', '', '')

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
        self.post_message(LogMessage(f'DataTable row selected: cursor_row={event.cursor_row}, key={event.row_key}'))
        table = self.query_one(DataTable)
        row_data = table.get_row_at(event.cursor_row)
        self.post_message(LogMessage(f'DataTable row data by index: {row_data}'))
        row_data = table.get_row(event.row_key)
        self.post_message(LogMessage(f'DataTable row data by key: {row_data}'))

        file_path = event.row_key.value
        video_file = self.video_files[file_path]
        # self.post_message(ShowMovieDetailsMessage(video_file))

        self.app.push_screen(ShowMovieDetailsModal(video_file), self.handle_movie_details_result)

    def handle_movie_details_result(self, button_id: str) -> None:
        self.post_message(LogMessage(f'Received ShowMovieDetails result: {button_id}'))


class VideoFileScannerModal(ModalScreen):
    CSS = """
        VideoFileScannerModal {
            align-horizontal: center;
            
            & > Vertical {
                width: auto;
                height: auto;
                offset-y: 25vh;
                border: round white;
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
        self.directory_scan_worker = self.run_worker(scan_folder(self.directory_path, _log_message, _scanning_complete, _add_video_file))
        self.post_message(LogMessage(f'Started worker to scan directory {self.directory_path}'))

    @on(Button.Pressed, '#cancel_id')
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'VideoFileScannerModal "Cancel" Button pressed'))

        if self.directory_scan_worker and self.directory_scan_worker.state == WorkerState.RUNNING:
            self.post_message(LogMessage(f'VideoFileScannerModal cancelling worker...'))
            self.directory_scan_worker.cancel()
            self.post_message(LogMessage(f'VideoFileScannerModal worker cancelled'))

        # I don't think we need to dismiss, since canceling the worker will trigger a call to _scanning_complete(), and that calls self.dismiss()
        # self.dismiss()


class VideoContentFetchModal(ModalScreen):
    CSS = """
        VideoContentFetchModal {
            align-horizontal: center;
            
            & > Vertical {
                width: auto;
                height: auto;
                offset-y: 25vh;
                border: round white;
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
        self.post_message(LogMessage(f'[VideoContentFetchModal] Starting worker to fetch IMDB details for {self.video_file.imdb_tt}...'))
        self.imdb_worker = self.run_worker(get_imdb_details(self.video_file.imdb_tt))
        self.post_message(LogMessage(f'[VideoContentFetchModal] Started worker to fetch IMDB details for {self.video_file.imdb_tt}'))

    @on(Button.Pressed, '#cancel_id')
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[VideoContentFetchModal] "Cancel" Button pressed'))

        if self.imdb_worker and self.imdb_worker.state == WorkerState.RUNNING:
            self.post_message(LogMessage(f'[VideoContentFetchModal] cancelling worker...'))
            self.imdb_worker.cancel()
            self.post_message(LogMessage(f'[VideoContentFetchModal] worker cancelled'))

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        self.post_message(LogMessage(f'[VideoContentFetchModal] Received worker state change event: state={event.state}'))

        if event.state == WorkerState.SUCCESS:
            self.post_message(LogMessage(f'[VideoContentFetchModal] Final worker result: result={self.imdb_worker.result}'))
            self.video_file.imdb_plot = self.imdb_worker.result.imdb_plot

        if event.state in [WorkerState.CANCELLED, WorkerState.ERROR, WorkerState.SUCCESS]:
            self.dismiss()


class ShowMovieDetailsModal(ModalScreen):
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
                Button('Cancel', compact=True, id='cancel_id')
            )
        )

    @on(Button.Pressed, '#fetch_details_id')
    def fetch_details_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed; showing VideoContentFetchModal'))
        self.app.push_screen(VideoContentFetchModal(self.video_file))

    @on(Button.Pressed, '#search_title_id')
    def search_title_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed'))

    @on(Button.Pressed, '#cancel_id')
    def cancel_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ShowMovieDetailsModal] Button {event.button.id} pressed'))
        self.dismiss(event.button.id)

    # def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
    #     self.post_message(LogMessage(f'ShowMovieDetails:on_worker_state_changed: state={event.state} result={self.imdb_worker.result}'))
    #
    #     if event.state == WorkerState.SUCCESS:
    #         imdb_plot = self.imdb_worker.result.imdb_plot
    #         text_area: TextArea = self.query_one('#plot_id', TextArea)
    #         text_area.text = imdb_plot


class MyApp(App):
    SCREENS = {'log_screen': LogScreen,
               'table_screen': TableScreen, }

    BINDINGS = [('m,escape', 'show_main_menu', 'Show Main Menu'),
                ('l', 'show_log_screen', 'Show Log Screen'),
                ('f', 'show_data_screen', 'Show Data Screen'), ]

    def __init__(self):
        super().__init__()
        self.log_screen = self.get_screen('log_screen', LogScreen)
        self.table_screen = self.get_screen('table_screen', TableScreen)
        self.directory_scan_worker: Worker | None = None
        self.video_files: dict[str, VideoFile] = dict()

    def on_mount(self) -> None:
        self.push_screen('log_screen')
        self.push_screen('table_screen')
        # self.run_worker(self.background_worker_task())
        self.action_show_main_menu()

    def action_show_main_menu(self):
        def _do_main_menu_action(action: MainMenu.MainMenuActions | None) -> None:
            if action is not None:
                self.log_message(f'Received MainMenuAction = {action.name}')

                if action == MainMenu.MainMenuActions.SAVE_VIDEO_LIST:
                    self.save_video_files()
                elif action == MainMenu.MainMenuActions.LOAD_VIDEO_LIST:
                    self.load_video_files()
                elif action == MainMenu.MainMenuActions.PICK_A_DIRECTORY:
                    self.pick_a_directory_and_start_scanning()
                elif action == MainMenu.MainMenuActions.SHOW_LOG_SCREEN:
                    self.switch_screen('log_screen')
                elif action == MainMenu.MainMenuActions.SHOW_TABLE_SCREEN:
                    self.switch_screen('table_screen')
                elif action == MainMenu.MainMenuActions.STOP_DIRECTORY_SCAN:
                    if self.directory_scan_worker and self.directory_scan_worker.state == WorkerState.RUNNING:
                        self.directory_scan_worker.cancel()

        if not isinstance(self.screen, MainMenu):
            self.push_screen(MainMenu(), _do_main_menu_action)

    def action_show_log_screen(self):
        self.switch_screen('log_screen')

    def action_show_data_screen(self):
        self.switch_screen('table_screen')

    @textual.on(LogMessage)
    def on_log_message(self, message: LogMessage) -> None:
        self.log_message(message.message)

    def log_message(self, message: str) -> None:
        log_screen = self.get_screen('log_screen', LogScreen)
        log_screen.info(message)

    def pick_a_directory_and_start_scanning(self) -> None:
        def _add_video_file(video_file: VideoFile) -> None:
            if video_file.file_path not in self.video_files:
                self.video_files[video_file.file_path] = video_file
                self.log_message(f'Adding video file: {video_file.file_path}')
                self.table_screen.add_video_file(video_file)
            else:
                self.log_message(f'Ignoring duplicate video file: {video_file.file_path}')

        def _pick_directory_result(directory_path: Path | None) -> Path | None:
            self.log_message(f'Selected directory: {directory_path}')
            if directory_path:
                self.push_screen(VideoFileScannerModal(directory_path, _add_video_file))

        self.push_screen(SelectDirectory(), _pick_directory_result)

    def load_video_files(self):
        def _file_open_result(file_path: Path | None) -> Path | None:
            self.log_message(f'Selected Load File: {file_path}')
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as file:
                    video_files_json = json.load(file)
                self.video_files = dict()
                for video_file_dict in video_files_json:
                    video_file_path = video_file_dict['file_path']
                    self.video_files[video_file_path] = VideoFile(**video_file_dict)
                self.table_screen.set_video_data(self.video_files)

        self.push_screen(FileOpen(), _file_open_result)

    def save_video_files(self):
        def _file_save_result(file_path: Path | None) -> Path | None:
            self.log_message(f'Selected Save File: {file_path}')
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write('[\n')
                    for i, video_file in enumerate(self.video_files.values()):
                        if i > 0:
                            file.write(',\n')
                        video_file_json = '  ' + json.dumps(dataclasses.asdict(video_file), ensure_ascii=False)
                        file.write(video_file_json)
                    file.write('\n]\n')

        self.push_screen(FileSave(), _file_save_result)

    # @textual.on(ShowMovieDetailsMessage)
    # def show_movie_details(self, show_movie_details_message: ShowMovieDetailsMessage) -> None:
    #     self.log_message(f'Showing movie details: {show_movie_details_message.video_file.file_path}')
    #     self.push_screen(ShowMovieDetails(show_movie_details_message.video_file))

    # async def background_worker_task(self):
    #     count = 1
    #     while True:
    #         self.on_log_message(LogMessage(f'Background Worker Count = {count}'))
    #         count += 1
    #         await asyncio.sleep(10.0)


if __name__ == '__main__':
    app = MyApp()
    app.run()
