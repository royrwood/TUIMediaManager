from enum import StrEnum

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, ListItem, ListView


class ChooseSortByOptionModal(ModalScreen):
    class SortByOptions(StrEnum):
        SORT_BY_NAME = 'Sort by Name'
        SORT_BY_FILEPATH = 'Sort by Filepath'
        SORT_BY_IMDB_TT = 'Sort by IMDB Number'

    CSS = """
         ChooseSortByOptionModal {
             align-horizontal: center;

             & > ListView {
                 width: auto;
                 height: auto;
                 offset-y: 25vh;
                 border: solid white;

                 & > ListItem {
                     width: auto;
                     min-width: 100%;
                     padding: 0 1;
                 }
             }
         }
     """

    BINDINGS = [('escape', 'do_cancel', 'Cancel')]

    def compose(self) -> ComposeResult:
        # Use a ListView so arrow keys can navigate up and down in the list
        with ListView():
            for menu_action in ChooseSortByOptionModal.SortByOptions:
                yield ListItem(Label(str(menu_action.value)), id=menu_action.name)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # sort_by_option = ChooseSortByOptionModal.SortByOptions[event.item.id]  # Pycharm linter complains about this because SortByOptions is a StrEnum, not a plain Enum
        sort_by_option = getattr(ChooseSortByOptionModal.SortByOptions, event.item.id)  # Pycharm linter likes this way of getting the enum by name-- FINE, WHATEVER.
        self.dismiss(sort_by_option)

    def action_do_cancel(self) -> None:
        self.dismiss(None)
