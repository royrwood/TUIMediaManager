from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, DataTable

from tui_media_manager.messages import LogMessage
from tui_media_manager.imdb.utils import IMDBInfo


class ReviewIMDBSearchResultsModal(ModalScreen):
    CSS = """
         ReviewIMDBSearchResultsModal {
             align: center middle;

             & > DataTable {
                 width: auto;
                 height: 80vh;
                 border: round $primary;
                 padding: 1 2;
             }
         }
     """

    BINDINGS = [('escape', 'do_cancel', 'Cancel')]

    def __init__(self, imdb_info_list: list[IMDBInfo]):
        super().__init__()
        self.imdb_info_list = imdb_info_list

        self.data_table = DataTable(show_header=True, cell_padding=2, header_height=1, cursor_type='row', id='imdb_result_table')
        self.data_table.add_columns('IMDB', 'Name', 'Year')
        for i, imdb_info in enumerate(self.imdb_info_list):
            self.data_table.add_row(imdb_info.imdb_tt, imdb_info.imdb_name, imdb_info.imdb_year, key=f'imdb_info_{i}')

    def compose(self) -> ComposeResult:
        yield self.data_table

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] DataTable row selected: cursor_row={event.cursor_row}, key={event.row_key.value}'))
        row_data = self.data_table.get_row_at(event.cursor_row)
        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] DataTable row data by index: {row_data}'))
        row_data = self.data_table.get_row(event.row_key)
        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] DataTable row data by key: {row_data}'))

    def action_do_cancel(self) -> None:
        self.dismiss(None)
