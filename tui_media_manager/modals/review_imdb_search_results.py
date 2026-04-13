from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, DataTable, Button
from textual.containers import Vertical, Horizontal

from tui_media_manager.messages import LogMessage
from tui_media_manager.imdb.utils import IMDBInfo
from tui_media_manager.modals.get_imdb_details import GetIMDBDetailsModal


class ReviewIMDBSearchResultsModal(ModalScreen):
    CSS = """
         ReviewIMDBSearchResultsModal {
             align: center middle;
        
            & > Vertical {
                min-width: 50vw;
                width: auto;
                height: auto;
                keyline: thin $primary;  # For keyline to work, all children must have margin 1 
        
                & > Label {
                    width: 100%;
                    height: auto;
                    margin: 1;
                    padding: 0 2;
                }
        
                & > DataTable {
                    width: 100%;
                    height: auto;
                    max-height: 60vh;
                    margin: 1;   
                }
        
                & > Horizontal {
                    width: 100%;
                    height: auto;  # Horizontal is greedy, so we need to force it to shrink-wrap its contents 
                    align-horizontal: right;
                    margin: 1;
        
                    & > Button {
                        margin: 0 1;
                    }
                }
            }
         }
     """

    BINDINGS = [('escape', 'do_cancel', 'Cancel')]

    def __init__(self, imdb_info_list: list[IMDBInfo]):
        super().__init__()
        self.imdb_info_list = imdb_info_list

        self.data_table = DataTable(show_header=True, cell_padding=2, header_height=1, cursor_type='row', id='imdb_result_table')
        self.data_table.add_columns('IMDB', 'Year', 'Name')
        for i, imdb_info in enumerate(self.imdb_info_list):
            self.data_table.add_row(imdb_info.imdb_tt, imdb_info.imdb_year, imdb_info.imdb_name, key=f'imdb_info_{i}')

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label('IMDB Search Results:'),
            self.data_table,
            Horizontal(
                Button('OK', compact=True, id='okay_id'),
                Button('Cancel', compact=True, id='cancel_id')
            )
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        def _get_imdb_details_callback(imdb_info: IMDBInfo):
            self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Got imdb_info: {imdb_info}'))

        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] DataTable row selected: cursor_row={event.cursor_row}, key={event.row_key.value}'))
        row_data = self.data_table.get_row_at(event.cursor_row)
        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] DataTable row data by index: {row_data}'))
        # row_data = self.data_table.get_row(event.row_key)
        # self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] DataTable row data by key: {row_data}'))

        imdb_tt = row_data[0]
        imdb_name = row_data[2]
        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Getting IMDB details for imdb_tt={imdb_tt}'))

        self.app.push_screen(GetIMDBDetailsModal(imdb_tt, imdb_name), _get_imdb_details_callback)

    def action_do_cancel(self) -> None:
        self.dismiss(None)
