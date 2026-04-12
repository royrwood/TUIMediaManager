from enum import StrEnum

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, ListItem, ListView


class MainMenuModal(ModalScreen):
    class MainMenuActions(StrEnum):
        SHOW_TABLE_SCREEN = 'Show Data Table'
        SHOW_LOG_SCREEN = 'Show Log'
        LOAD_VIDEO_LIST = 'Load Video Data'
        SAVE_VIDEO_LIST = 'Save Video Data'
        PICK_A_DIRECTORY = 'Pick a Directory'

    CSS = """
         MainMenuModal {
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

    BINDINGS = [('escape', 'do_cancel', 'Cancel')]

    def compose(self) -> ComposeResult:
        # Use a ListView so arrow keys can navigate up and down in the list
        with ListView():
            for menu_action in MainMenuModal.MainMenuActions:
                yield ListItem(Label(str(menu_action.value)), id=menu_action.name)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # main_menu_actions_enum = MainMenuActions[event.item.id]  # Pycharm linter complains about this because MainMenuActions is a StrEnum, not a plain Enum
        main_menu_actions_enum = getattr(MainMenuModal.MainMenuActions, event.item.id)  # Pycharm linter likes this way of getting the enum by name-- FINE, WHATEVER.
        self.dismiss(main_menu_actions_enum)

    def action_do_cancel(self) -> None:
        self.dismiss(None)
