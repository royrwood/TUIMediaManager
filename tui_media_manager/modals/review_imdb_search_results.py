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

    def __init__(self, imdb_info_list: list[IMDBInfo]):
        super().__init__()
        self.imdb_info_list = imdb_info_list
        self.imdb_response_info_by_row_key = dict()

        self.data_table = DataTable(show_header=True, cell_padding=2, header_height=1, cursor_type='row', id='imdb_result_table')
        self.column_keys = self.data_table.add_columns('IMDB', 'Year', 'Name')
        for i, imdb_info in enumerate(self.imdb_info_list):
            self.data_table.add_row(f'[dim]{imdb_info.imdb_tt}[/dim]', f'[dim]{imdb_info.imdb_year}[/dim]', f'[dim]{imdb_info.imdb_name}[/dim]', key=f'imdb_info_{i}')

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

        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Reviewing IMDB results for {imdb_info.imdb_tt} {imdb_info.imdb_name}'))
        self.app.push_screen(ShowIMDBInfoModal(imdb_info), _imdb_info_review_callback)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        def _get_imdb_details_callback(imdb_info: IMDBInfo):
            self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Got IMDB details: imdb_info={imdb_info}'))

            if imdb_info:
                self.imdb_response_info_by_row_key[event.row_key.value] = imdb_info
                self.data_table.update_cell(event.row_key, self.column_keys[0], f'[bold]{imdb_info.imdb_tt}[/bold]')
                self.data_table.update_cell(event.row_key, self.column_keys[1], f'[bold]{imdb_info.imdb_year}[/bold]')
                self.data_table.update_cell(event.row_key, self.column_keys[2], f'[bold]{imdb_info.imdb_name}[/bold]')
                self.review_imdb_details(imdb_info)

        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] DataTable row selected: cursor_row={event.cursor_row}, key={event.row_key.value}'))
        selected_imdb_info = self.imdb_info_list[event.cursor_row]
        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Getting and reviewing IMDB details for imdb_tt={selected_imdb_info.imdb_tt} imdb_name={selected_imdb_info.imdb_name}'))
        self.app.push_screen(GetIMDBDetailsModal(selected_imdb_info.imdb_tt, selected_imdb_info.imdb_name), _get_imdb_details_callback)

    @on(Button.Pressed, '#accept_id')
    def accept_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ReviewIMDBSearchResultsModal] Button {event.button.id} pressed'))
        # self.dismiss(imdb_info)

    @on(Button.Pressed, '#cancel_id')
    def accept_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_do_cancel(self) -> None:
        self.dismiss(None)
