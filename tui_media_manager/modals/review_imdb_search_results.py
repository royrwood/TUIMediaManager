from textual import on
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, DataTable, Button
from textual.containers import Vertical, Horizontal

from tui_media_manager.messages import LogMessage
from tui_media_manager.imdb.utils import IMDBInfo
from tui_media_manager.modals.get_imdb_details import GetIMDBDetailsModal
from tui_media_manager.modals.view_imdb_info import ShowIMDBInfoModal


class ReviewIMDBSearchResultsModal(ModalScreen[IMDBInfo]):
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
    AUTO_FOCUS = "#accept_id"

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
                Button('Accept', compact=True, id='accept_id'),
                Button('Cancel', compact=True, id='cancel_id')
            )
        )

    def review_imdb_details(self, imdb_info: IMDBInfo):
        def _imdb_info_review_callback(accepted_imdb_info: IMDBInfo):
            self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Got ShowIMDBInfoModal response: imdb_info={accepted_imdb_info}'))
            if accepted_imdb_info:
                self.dismiss(accepted_imdb_info)

        self.app.push_screen(ShowIMDBInfoModal(imdb_info), _imdb_info_review_callback)

    def get_imdb_info_and_review_or_dismiss(self, cursor_row: int, review_results: bool) -> None:
        def _get_imdb_details_callback(imdb_info: IMDBInfo):
            self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Got IMDB details: imdb_info={imdb_info}'))

            if imdb_info and review_results:
                self.review_imdb_details(imdb_info)
            else:
                self.dismiss(imdb_info)

        row_data = self.data_table.get_row_at(cursor_row)
        imdb_tt = row_data[0]
        imdb_name = row_data[2]

        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Getting IMDB details for imdb_tt={imdb_tt} imdb_name={imdb_name}'))
        self.app.push_screen(GetIMDBDetailsModal(imdb_tt, imdb_name), _get_imdb_details_callback)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] DataTable row selected: cursor_row={event.cursor_row}, key={event.row_key.value}'))
        self.get_imdb_info_and_review_or_dismiss(event.cursor_row, review_results=True)

    @on(Button.Pressed, '#accept_id')
    def accept_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Button {event.button.id} pressed'))
        self.get_imdb_info_and_review_or_dismiss(self.data_table.cursor_coordinate.row, review_results=False)

    def action_do_cancel(self) -> None:
        self.dismiss(None)
