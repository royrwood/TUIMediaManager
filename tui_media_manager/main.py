from textual.app import App
import textual

from tui_media_manager.messages import LogMessage
from tui_media_manager.modals.main_menu import MainMenuModal
from tui_media_manager.modals.button_choices import ButtonChoicesModal
from tui_media_manager.screens.runtime_log import RuntimeLogScreen
from tui_media_manager.screens.video_list_screen import VideoListScreen


class MyApp(App):
    SCREENS = {'log_screen': RuntimeLogScreen,
               'table_screen': VideoListScreen, }

    BINDINGS = [('m,escape', 'show_main_menu', 'Show Main Menu'),
                ('l', 'show_log_screen', 'Show Log Screen'),
                ('f', 'show_data_screen', 'Show Data Screen'),
                ('t', 'test_dialog', 'Test Dialog'), ]

    def __init__(self):
        super().__init__()
        self.log_screen = self.get_screen('log_screen', RuntimeLogScreen)
        self.table_screen = self.get_screen('table_screen', VideoListScreen)

    def on_mount(self) -> None:
        self.push_screen('log_screen')
        self.push_screen('table_screen')
        self.action_show_main_menu()

    def action_show_main_menu(self):
        def _do_main_menu_action(action: MainMenuModal.MainMenuActions | None) -> None:
            if action is not None:
                self.log_message(f'Received MainMenuAction = {action.name}')

                if action == MainMenuModal.MainMenuActions.SAVE_VIDEO_LIST:
                    self.table_screen.save_video_files()
                elif action == MainMenuModal.MainMenuActions.LOAD_VIDEO_LIST:
                    self.table_screen.load_video_files()
                elif action == MainMenuModal.MainMenuActions.PICK_A_DIRECTORY:
                    self.table_screen.pick_a_directory_and_start_scanning()
                elif action == MainMenuModal.MainMenuActions.SHOW_LOG_SCREEN:
                    self.switch_screen('log_screen')
                elif action == MainMenuModal.MainMenuActions.SHOW_TABLE_SCREEN:
                    self.switch_screen('table_screen')
                elif action == MainMenuModal.MainMenuActions.TEST_DIALOG:
                    self.action_test_dialog()

        if not isinstance(self.screen, MainMenuModal):
            self.push_screen(MainMenuModal(), _do_main_menu_action)

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

    def action_test_dialog(self):
        self.push_screen(ButtonChoicesModal('This is a test', ['One', 'Two', 'Three']))


if __name__ == '__main__':
    app = MyApp()
    app.run()
