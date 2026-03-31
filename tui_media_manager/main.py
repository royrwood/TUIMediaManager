from enum import StrEnum
from pathlib import Path
import asyncio
import dataclasses
import json
import logging
import os
import re

import aiohttp
import textual
from textual.worker import Worker
from textual.app import App, ComposeResult
from textual.message import Message
from textual.screen import Screen, ModalScreen
from textual.widgets import DataTable, Label, ListItem, ListView, Log, Footer

from textual_fspicker import SelectDirectory


LOGGER = logging.getLogger(__name__)
logging.basicConfig(filename='mini_media_manager.log', encoding='utf-8', level=logging.INFO)
LOGGER.info('Starting up...')


class MainMenuActions(StrEnum):
    SHOW_TABLE_SCREEN = "Show Data Table"
    SHOW_LOG_SCREEN = "Show Log"
    PICK_A_DIRECTORY = "Pick a Directory"
    STOP_DIRECTORY_SCAN = "Stop Directory Scan"


class LogMessage(Message):
    def __init__(self, message: str, level=0):
        super().__init__()
        self.message = message
        self.level = level


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


class MainMenu(ModalScreen):
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

    BINDINGS = [("escape", "cancel_menu", "Cancel Menu")]

    def compose(self) -> ComposeResult:
        # Use a ListView so arrow keys can navigate up and down in the list
        with ListView():
            for menu_action in MainMenuActions:
                yield ListItem(Label(str(menu_action.value)), id=menu_action.name)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # main_menu_actions_enum = MainMenuActions[event.item.id]  # Pycharm linter complains about this because MainMenuActions is a StrEnum, not a plain Enum
        main_menu_actions_enum = getattr(MainMenuActions, event.item.id)  # Pycharm linter likes this way of getting the enum by name-- FINE, WHATEVER.
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
    def compose(self) -> ComposeResult:
        yield DataTable(show_header=True, cell_padding=2, header_height=1, cursor_type="row", id="video_files")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns('IMDB', 'Name', 'Year', 'File')
        # table.add_row('', '', '', '')

    def add_video_file(self, video_file: VideoFile):
        data_table = self.query_one(DataTable)
        video_filename = Path(video_file.file_path).name
        data_table.add_row(video_file.imdb_tt, video_file.imdb_name, video_file.imdb_year, video_filename, key=video_file.imdb_tt)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.post_message(LogMessage(f"DataTable row selected: cursor_row={event.cursor_row}, key={event.row_key}"))
        table = self.query_one(DataTable)
        row_data = table.get_row_at(event.cursor_row)
        self.post_message(LogMessage(f"DataTable row data by index: {row_data}"))
        row_data = table.get_row(event.row_key)
        self.post_message(LogMessage(f"DataTable row data by key: {row_data}"))

    @staticmethod
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

    async def get_imdb_basic_info(self, video_name: str, year: str | None, num_matches: int = 1) -> list[IMDBInfo]:
        # curl -s -H 'Content-Type: application/json' -d @imdb_graphql_simple.json 'https://api.graphql.imdb.com/'

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
            self.post_message(LogMessage(f"Getting IMDB basic info for {video_name} {year}"))

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
                        self.post_message(LogMessage(f"Found IMDB {imdb_info.imdb_tt} {imdb_info.imdb_name} ({imdb_info.imdb_year})"))
                    return imdb_info_list

    async def scan_folder(self, folder_path: Path, include_extensions: str = None) -> None:
        if include_extensions is None:
            include_extensions = 'mkv,mp4'

        include_extensions_list = [ext.lower().strip() for ext in include_extensions.split(',')]

        self.post_message(LogMessage(f"Beginning processing of directory: {str(folder_path)}"))

        for dir_path, dirs, files in os.walk(folder_path):
            for filename in files:
                file_path = os.path.join(dir_path, filename)
                filename_parts = os.path.splitext(filename)
                filename_no_extension = filename_parts[0]
                filename_extension = filename_parts[1]
                if filename_extension.startswith('.'):
                    filename_extension = filename_extension[1:]

                if filename_extension.lower() not in include_extensions_list:
                    continue

                scrubbed_video_file_name, year = self.scrub_video_file_name(filename_no_extension)
                video_file = VideoFile(file_path=file_path, scrubbed_file_name=scrubbed_video_file_name, scrubbed_file_year=year)

                self.post_message(LogMessage(f"Getting IMDB info for video file: {file_path}"))
                imdb_info_list = await self.get_imdb_basic_info(video_file.scrubbed_file_name, video_file.scrubbed_file_year, num_matches=1)
                imdb_info = imdb_info_list[0]
                if imdb_info:
                    self.post_message(LogMessage(f"Found: tt={imdb_info.imdb_tt}, name={imdb_info.imdb_name}, year={imdb_info.imdb_year}"))
                    video_file.imdb_tt = imdb_info.imdb_tt
                    video_file.imdb_name = imdb_info.imdb_name
                    video_file.imdb_year = imdb_info.imdb_year
                    video_file.imdb_rating = imdb_info.imdb_rating
                    video_file.imdb_plot = imdb_info.imdb_plot
                    video_file.imdb_genres = imdb_info.imdb_genres

                    self.post_message(LogMessage(f"Processed video file: {file_path}"))
                    self.add_video_file(video_file)

                await asyncio.sleep(1.0)

        self.post_message(LogMessage(f"End processing of directory: {str(folder_path)}"))


class MyApp(App):
    SCREENS = {"log_screen": LogScreen,
               "table_screen": TableScreen, }

    BINDINGS = [("m,escape", "show_main_menu", "Show Main Menu"),
                ('l', 'show_log_screen', 'Show Log Screen'),
                ('f', 'show_data_screen', 'Show Data Screen'), ]

    def __init__(self):
        super().__init__()
        self.log_screen = self.get_screen("log_screen", LogScreen)
        self.table_screen = self.get_screen("table_screen", TableScreen)
        self.directory_scan_worker: Worker | None = None

    def on_mount(self) -> None:
        self.push_screen('log_screen')
        self.push_screen('table_screen')
        self.run_worker(self.background_worker_task())
        self.action_show_main_menu()

    def action_show_main_menu(self):
        if not isinstance(self.screen, MainMenu):
            self.push_screen(MainMenu(), self.do_main_menu_action)

    def action_show_log_screen(self):
        self.switch_screen('log_screen')

    def action_show_data_screen(self):
        self.switch_screen('table_screen')

    def do_main_menu_action(self, action: MainMenuActions | None) -> None:
        if action is not None:
            self.log_message(f'Received MainMenuAction = {action.name}')

            if action == MainMenuActions.PICK_A_DIRECTORY:
                self.pick_a_directory()
            elif action == MainMenuActions.SHOW_LOG_SCREEN:
                self.switch_screen('log_screen')
            elif action == MainMenuActions.SHOW_TABLE_SCREEN:
                self.switch_screen('table_screen')
            elif action == MainMenuActions.STOP_DIRECTORY_SCAN:
                pass

    @textual.on(LogMessage)
    def on_log_message(self, message: LogMessage) -> None:
        self.log_message(message.message)

    def log_message(self, message: str) -> None:
        log_screen = self.get_screen("log_screen", LogScreen)
        log_screen.info(message)

    def pick_a_directory(self) -> None:
        def _pick_directory_result(directory_path: Path | None) -> Path | None:
            self.log_message(f'Selected directory: {directory_path}')
            if directory_path:
                self.log_message(f'Starting worker to scan directory: {directory_path}')
                self.directory_scan_worker = self.run_worker(self.table_screen.scan_folder(directory_path))
                self.log_message(f'Started worker to scan directory: {directory_path}')

        self.push_screen(SelectDirectory(), _pick_directory_result)

    async def background_worker_task(self):
        count = 1
        while True:
            self.on_log_message(LogMessage(f'Background Worker Count = {count}'))
            count += 1
            await asyncio.sleep(2.0)


if __name__ == "__main__":
    app = MyApp()
    app.run()
