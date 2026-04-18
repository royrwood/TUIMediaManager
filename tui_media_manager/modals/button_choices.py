from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal

from tui_media_manager.messages import LogMessage


class ButtonChoicesModal(ModalScreen[str]):
    CSS = """
        ButtonChoicesModal {
            align-horizontal: center;
            
            & > Vertical {
                width: auto;
                height: auto;
                offset-y: 25vh;
                border: round $primary;
                padding: 1 2;
                
                & > Label {
                    width: 100%;
                    margin-bottom: 1;
                }
                                
                & > Horizontal {
                    width: auto;
                    height: auto;
                    align-horizontal: right;
                
                    & > Button {
                        width: auto;
                        margin: 0 1;
                    }
                }
            }
        }   
     """

    def __init__(self, prompt: str, button_text_list: list[str]):
        super().__init__()
        self.prompt = Label(prompt)
        self.buttons = [Button(text, compact=True, id=f'button_{i}') for i, text in enumerate(button_text_list)]

    def compose(self) -> ComposeResult:
        yield Vertical(
            self.prompt,
            Horizontal(*self.buttons)
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(LogMessage(f'[ButtonChoicesModal] Button pressed: {event.button.id}'))
        self.dismiss(event.button.id)
