import tkinter as tk
import pyautogui

class AlphaNumericKeyboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Alpha Numeric Keyboard")
        self.create_keyboard()

    def create_keyboard(self):
        buttons = [
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
            'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P',
            'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L',
            'Z', 'X', 'C', 'V', 'B', 'N', 'M',
            'Space', 'Enter', 'Backspace'
        ]

        row = 0
        col = 0
        for button in buttons:
            if button == 'Space':
                tk.Button(self.root, text=button, width=20, command=lambda b=button: self.on_button_click(b)).grid(row=row, column=col, columnspan=5)
                col += 5
            else:
                tk.Button(self.root, text=button, width=5, command=lambda b=button: self.on_button_click(b)).grid(row=row, column=col)
                col += 1
            if col > 9:
                col = 0
                row += 1

    def on_button_click(self, button):
        if button == 'Space':
            pyautogui.write(' ')
        elif button == 'Enter':
            pyautogui.press('enter')
        elif button == 'Backspace':
            pyautogui.press('backspace')
        else:
            pyautogui.write(button)

if __name__ == "__main__":
    root = tk.Tk()
    keyboard = AlphaNumericKeyboard(root)
    root.mainloop()
