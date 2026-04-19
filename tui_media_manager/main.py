from enum import StrEnum

from textual.app import App
import textual

from tui_media_manager.messages import LogMessage
from tui_media_manager.modals.popup_menu import PopupMenuModal
from tui_media_manager.screens.runtime_log import RuntimeLogScreen
from tui_media_manager.screens.video_list_screen import VideoListScreen


class MyApp(App):
    class MainMenuActions(StrEnum):
        SHOW_TABLE_SCREEN = 'Show Data Table'
        SHOW_LOG_SCREEN = 'Show Log'
        LOAD_VIDEO_LIST = 'Load Video Data'
        SAVE_VIDEO_LIST = 'Save Video Data'
        PICK_A_DIRECTORY = 'Pick a Directory'

    SCREENS = {'log_screen': RuntimeLogScreen,
               'table_screen': VideoListScreen, }

    BINDINGS = [('m,escape', 'show_main_menu', 'Show Main Menu'),
                ('l', 'show_log_screen', 'Show Log Screen'),
                ('f', 'show_data_screen', 'Show Data Screen')]

    def __init__(self):
        super().__init__()
        self.log_screen = self.get_screen('log_screen', RuntimeLogScreen)
        self.table_screen = self.get_screen('table_screen', VideoListScreen)

    def on_mount(self) -> None:
        self.push_screen('log_screen')
        self.push_screen('table_screen')
        self.action_show_main_menu()

    def action_show_main_menu(self):
        def _do_main_menu_action(action: MyApp.MainMenuActions | None) -> None:
            if action is not None:
                self.log_message(f'Received MainMenuAction = {action.name}')

                if action == MyApp.MainMenuActions.SAVE_VIDEO_LIST:
                    self.table_screen.save_video_files()
                elif action == MyApp.MainMenuActions.LOAD_VIDEO_LIST:
                    self.table_screen.load_video_files()
                elif action == MyApp.MainMenuActions.PICK_A_DIRECTORY:
                    self.table_screen.pick_a_directory_and_start_scanning()
                elif action == MyApp.MainMenuActions.SHOW_LOG_SCREEN:
                    self.switch_screen('log_screen')
                elif action == MyApp.MainMenuActions.SHOW_TABLE_SCREEN:
                    self.switch_screen('table_screen')

        if not isinstance(self.screen, PopupMenuModal):
            self.push_screen(PopupMenuModal(MyApp.MainMenuActions), _do_main_menu_action)

    def action_show_log_screen(self):
        self.switch_screen('log_screen')

    def action_show_data_screen(self):
        self.switch_screen('table_screen')

    @textual.on(LogMessage)
    def on_log_message(self, message: LogMessage) -> None:
        self.log_message(message.message)

    def log_message(self, message: str) -> None:
        log_screen = self.get_screen('log_screen', RuntimeLogScreen)
        log_screen.info(message)


if __name__ == '__main__':
    app = MyApp()
    app.run()
