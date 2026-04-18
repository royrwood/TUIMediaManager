from enum import StrEnum
from typing import Type

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, ListItem, ListView


class PopupMenuModal(ModalScreen[StrEnum]):
    CSS = """
         PopupMenuModal {
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

    def __init__(self, menu_choice_enums: Type[StrEnum]) -> None:
        super().__init__()
        self.menu_choice_enums = menu_choice_enums

    def compose(self) -> ComposeResult:
        # Use a ListView so arrow keys can navigate up and down in the list
        with ListView():
            for choice_enum in self.menu_choice_enums:
                yield ListItem(Label(str(choice_enum.value)), id=choice_enum.name)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # choice_enum = self.menu_option_enums[event.item.id]  # Pycharm linter complains about this because SortByOptions is a StrEnum, not a plain Enum
        choice_enum = getattr(self.menu_choice_enums, event.item.id)  # Pycharm linter likes this way of getting the enum by name-- FINE, WHATEVER.
        self.dismiss(choice_enum)

    def action_do_cancel(self) -> None:
        self.dismiss(None)
