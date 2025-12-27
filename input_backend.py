"""
Wayland-compatible input simulation backend using python-evdev.
Provides PyAutoGUI-compatible API for keyboard and mouse operations.
"""

import time
from evdev import UInput, ecodes as e


class InputSimulator:
    """
    Simulates keyboard and mouse input using evdev (Wayland-compatible).
    API designed to match PyAutoGUI for drop-in replacement.
    """

    # Key name to evdev keycode mapping
    KEY_MAP = {
        # Letters (lowercase)
        'a': e.KEY_A, 'b': e.KEY_B, 'c': e.KEY_C, 'd': e.KEY_D,
        'e': e.KEY_E, 'f': e.KEY_F, 'g': e.KEY_G, 'h': e.KEY_H,
        'i': e.KEY_I, 'j': e.KEY_J, 'k': e.KEY_K, 'l': e.KEY_L,
        'm': e.KEY_M, 'n': e.KEY_N, 'o': e.KEY_O, 'p': e.KEY_P,
        'q': e.KEY_Q, 'r': e.KEY_R, 's': e.KEY_S, 't': e.KEY_T,
        'u': e.KEY_U, 'v': e.KEY_V, 'w': e.KEY_W, 'x': e.KEY_X,
        'y': e.KEY_Y, 'z': e.KEY_Z,

        # Numbers
        '0': e.KEY_0, '1': e.KEY_1, '2': e.KEY_2, '3': e.KEY_3,
        '4': e.KEY_4, '5': e.KEY_5, '6': e.KEY_6, '7': e.KEY_7,
        '8': e.KEY_8, '9': e.KEY_9,

        # Special keys
        'enter': e.KEY_ENTER, 'return': e.KEY_ENTER,
        'backspace': e.KEY_BACKSPACE,
        'tab': e.KEY_TAB,
        'space': e.KEY_SPACE,
        'escape': e.KEY_ESC, 'esc': e.KEY_ESC,

        # Arrow keys
        'up': e.KEY_UP, 'down': e.KEY_DOWN,
        'left': e.KEY_LEFT, 'right': e.KEY_RIGHT,

        # Navigation
        'home': e.KEY_HOME, 'end': e.KEY_END,
        'pageup': e.KEY_PAGEUP, 'pagedown': e.KEY_PAGEDOWN,
        'insert': e.KEY_INSERT, 'delete': e.KEY_DELETE,

        # Modifiers
        'shift': e.KEY_LEFTSHIFT, 'leftshift': e.KEY_LEFTSHIFT,
        'rightshift': e.KEY_RIGHTSHIFT,
        'ctrl': e.KEY_LEFTCTRL, 'control': e.KEY_LEFTCTRL,
        'leftctrl': e.KEY_LEFTCTRL, 'rightctrl': e.KEY_RIGHTCTRL,
        'alt': e.KEY_LEFTALT, 'leftalt': e.KEY_LEFTALT,
        'rightalt': e.KEY_RIGHTALT,
        'super': e.KEY_LEFTMETA, 'win': e.KEY_LEFTMETA,
        'meta': e.KEY_LEFTMETA,

        # Function keys
        'f1': e.KEY_F1, 'f2': e.KEY_F2, 'f3': e.KEY_F3, 'f4': e.KEY_F4,
        'f5': e.KEY_F5, 'f6': e.KEY_F6, 'f7': e.KEY_F7, 'f8': e.KEY_F8,
        'f9': e.KEY_F9, 'f10': e.KEY_F10, 'f11': e.KEY_F11, 'f12': e.KEY_F12,
    }

    # Character to (keycode, modifiers) mapping for write() method
    CHAR_MAP = {
        # Lowercase letters
        'a': (e.KEY_A, []), 'b': (e.KEY_B, []), 'c': (e.KEY_C, []),
        'd': (e.KEY_D, []), 'e': (e.KEY_E, []), 'f': (e.KEY_F, []),
        'g': (e.KEY_G, []), 'h': (e.KEY_H, []), 'i': (e.KEY_I, []),
        'j': (e.KEY_J, []), 'k': (e.KEY_K, []), 'l': (e.KEY_L, []),
        'm': (e.KEY_M, []), 'n': (e.KEY_N, []), 'o': (e.KEY_O, []),
        'p': (e.KEY_P, []), 'q': (e.KEY_Q, []), 'r': (e.KEY_R, []),
        's': (e.KEY_S, []), 't': (e.KEY_T, []), 'u': (e.KEY_U, []),
        'v': (e.KEY_V, []), 'w': (e.KEY_W, []), 'x': (e.KEY_X, []),
        'y': (e.KEY_Y, []), 'z': (e.KEY_Z, []),

        # Uppercase letters
        'A': (e.KEY_A, [e.KEY_LEFTSHIFT]), 'B': (e.KEY_B, [e.KEY_LEFTSHIFT]),
        'C': (e.KEY_C, [e.KEY_LEFTSHIFT]), 'D': (e.KEY_D, [e.KEY_LEFTSHIFT]),
        'E': (e.KEY_E, [e.KEY_LEFTSHIFT]), 'F': (e.KEY_F, [e.KEY_LEFTSHIFT]),
        'G': (e.KEY_G, [e.KEY_LEFTSHIFT]), 'H': (e.KEY_H, [e.KEY_LEFTSHIFT]),
        'I': (e.KEY_I, [e.KEY_LEFTSHIFT]), 'J': (e.KEY_J, [e.KEY_LEFTSHIFT]),
        'K': (e.KEY_K, [e.KEY_LEFTSHIFT]), 'L': (e.KEY_L, [e.KEY_LEFTSHIFT]),
        'M': (e.KEY_M, [e.KEY_LEFTSHIFT]), 'N': (e.KEY_N, [e.KEY_LEFTSHIFT]),
        'O': (e.KEY_O, [e.KEY_LEFTSHIFT]), 'P': (e.KEY_P, [e.KEY_LEFTSHIFT]),
        'Q': (e.KEY_Q, [e.KEY_LEFTSHIFT]), 'R': (e.KEY_R, [e.KEY_LEFTSHIFT]),
        'S': (e.KEY_S, [e.KEY_LEFTSHIFT]), 'T': (e.KEY_T, [e.KEY_LEFTSHIFT]),
        'U': (e.KEY_U, [e.KEY_LEFTSHIFT]), 'V': (e.KEY_V, [e.KEY_LEFTSHIFT]),
        'W': (e.KEY_W, [e.KEY_LEFTSHIFT]), 'X': (e.KEY_X, [e.KEY_LEFTSHIFT]),
        'Y': (e.KEY_Y, [e.KEY_LEFTSHIFT]), 'Z': (e.KEY_Z, [e.KEY_LEFTSHIFT]),

        # Numbers
        '0': (e.KEY_0, []), '1': (e.KEY_1, []), '2': (e.KEY_2, []),
        '3': (e.KEY_3, []), '4': (e.KEY_4, []), '5': (e.KEY_5, []),
        '6': (e.KEY_6, []), '7': (e.KEY_7, []), '8': (e.KEY_8, []),
        '9': (e.KEY_9, []),

        # Symbols (shifted numbers)
        '!': (e.KEY_1, [e.KEY_LEFTSHIFT]), '@': (e.KEY_2, [e.KEY_LEFTSHIFT]),
        '#': (e.KEY_3, [e.KEY_LEFTSHIFT]), '$': (e.KEY_4, [e.KEY_LEFTSHIFT]),
        '%': (e.KEY_5, [e.KEY_LEFTSHIFT]), '^': (e.KEY_6, [e.KEY_LEFTSHIFT]),
        '&': (e.KEY_7, [e.KEY_LEFTSHIFT]), '*': (e.KEY_8, [e.KEY_LEFTSHIFT]),
        '(': (e.KEY_9, [e.KEY_LEFTSHIFT]), ')': (e.KEY_0, [e.KEY_LEFTSHIFT]),

        # Special characters
        ' ': (e.KEY_SPACE, []),
        '\n': (e.KEY_ENTER, []),
        '\t': (e.KEY_TAB, []),
        '-': (e.KEY_MINUS, []),
        '_': (e.KEY_MINUS, [e.KEY_LEFTSHIFT]),
        '=': (e.KEY_EQUAL, []),
        '+': (e.KEY_EQUAL, [e.KEY_LEFTSHIFT]),
        '[': (e.KEY_LEFTBRACE, []),
        '{': (e.KEY_LEFTBRACE, [e.KEY_LEFTSHIFT]),
        ']': (e.KEY_RIGHTBRACE, []),
        '}': (e.KEY_RIGHTBRACE, [e.KEY_LEFTSHIFT]),
        '\\': (e.KEY_BACKSLASH, []),
        '|': (e.KEY_BACKSLASH, [e.KEY_LEFTSHIFT]),
        ';': (e.KEY_SEMICOLON, []),
        ':': (e.KEY_SEMICOLON, [e.KEY_LEFTSHIFT]),
        "'": (e.KEY_APOSTROPHE, []),
        '"': (e.KEY_APOSTROPHE, [e.KEY_LEFTSHIFT]),
        ',': (e.KEY_COMMA, []),
        '<': (e.KEY_COMMA, [e.KEY_LEFTSHIFT]),
        '.': (e.KEY_DOT, []),
        '>': (e.KEY_DOT, [e.KEY_LEFTSHIFT]),
        '/': (e.KEY_SLASH, []),
        '?': (e.KEY_SLASH, [e.KEY_LEFTSHIFT]),
        '`': (e.KEY_GRAVE, []),
        '~': (e.KEY_GRAVE, [e.KEY_LEFTSHIFT]),
    }

    def __init__(self):
        """Initialize virtual keyboard and mouse devices."""
        # Create virtual keyboard device with all keys
        kbd_capabilities = {
            e.EV_KEY: list(e.keys.keys())
        }
        self.kbd = UInput(kbd_capabilities, name='whisper-keyboard')

        # Create virtual mouse device
        mouse_capabilities = {
            e.EV_KEY: [e.BTN_LEFT, e.BTN_MIDDLE, e.BTN_RIGHT],
            e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL]
        }
        self.mouse = UInput(mouse_capabilities, name='whisper-mouse')

        # Small delay for device initialization
        time.sleep(0.1)

    def _press_key(self, keycode):
        """Press a key (key down event)."""
        self.kbd.write(e.EV_KEY, keycode, 1)
        self.kbd.syn()

    def _release_key(self, keycode):
        """Release a key (key up event)."""
        self.kbd.write(e.EV_KEY, keycode, 0)
        self.kbd.syn()

    def _tap_key(self, keycode, modifiers=None):
        """Press and release a key, optionally with modifiers."""
        if modifiers is None:
            modifiers = []

        # Press modifiers
        for mod in modifiers:
            self._press_key(mod)
            time.sleep(0.01)

        # Press and release main key
        self._press_key(keycode)
        time.sleep(0.01)
        self._release_key(keycode)

        # Release modifiers
        for mod in reversed(modifiers):
            self._release_key(mod)

        time.sleep(0.01)

    def hotkey(self, *keys):
        """
        Simulate a hotkey combination (e.g., Ctrl+C).

        Args:
            *keys: Variable number of key names (e.g., 'ctrl', 'c')

        Example:
            hotkey('ctrl', 'c')  # Simulates Ctrl+C
            hotkey('enter')       # Simulates Enter key
        """
        if not keys:
            return

        # Convert key names to keycodes
        keycodes = []
        for key in keys:
            key_lower = key.lower()
            if key_lower in self.KEY_MAP:
                keycodes.append(self.KEY_MAP[key_lower])
            else:
                print(f"Warning: Unknown key '{key}' in hotkey")
                return

        # Press all keys in sequence
        for keycode in keycodes:
            self._press_key(keycode)
            time.sleep(0.01)

        # Release all keys in reverse order
        for keycode in reversed(keycodes):
            self._release_key(keycode)

        time.sleep(0.01)

    def write(self, text, interval=0.01):
        """
        Type text character by character.

        Args:
            text: String to type
            interval: Delay between keystrokes (seconds)
        """
        for char in text:
            if char in self.CHAR_MAP:
                keycode, modifiers = self.CHAR_MAP[char]
                self._tap_key(keycode, modifiers)
                time.sleep(interval)
            else:
                # Unknown character - try to handle Unicode
                print(f"Warning: Character '{char}' (U+{ord(char):04X}) not in character map")

    def click(self, button='left'):
        """
        Simulate a mouse click at current cursor position.

        Args:
            button: 'left', 'middle', or 'right' (default: 'left')
        """
        btn_map = {
            'left': e.BTN_LEFT,
            'middle': e.BTN_MIDDLE,
            'right': e.BTN_RIGHT
        }

        btn_code = btn_map.get(button, e.BTN_LEFT)

        # Press button
        self.mouse.write(e.EV_KEY, btn_code, 1)
        self.mouse.syn()
        time.sleep(0.01)

        # Release button
        self.mouse.write(e.EV_KEY, btn_code, 0)
        self.mouse.syn()
        time.sleep(0.01)

    def middleClick(self):
        """Simulate a middle mouse click (PyAutoGUI compatibility)."""
        self.click('middle')

    def rightClick(self):
        """Simulate a right mouse click (PyAutoGUI compatibility)."""
        self.click('right')

    def prompt(self, title='', text='', default=''):
        """
        Display a simple input dialog using tkinter.

        Args:
            title: Dialog title
            text: Prompt text
            default: Default value

        Returns:
            User input string, or None if cancelled
        """
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()  # Hide main window
        result = simpledialog.askstring(title, text, initialvalue=default)
        root.destroy()

        return result

    def __del__(self):
        """Clean up virtual devices on object destruction."""
        try:
            self.kbd.close()
            self.mouse.close()
        except:
            pass


# For testing
if __name__ == '__main__':
    print("Testing InputSimulator...")
    sim = InputSimulator()

    print("Testing write...")
    time.sleep(2)
    sim.write("Hello World!\n")

    print("Testing hotkeys...")
    time.sleep(1)
    sim.hotkey('ctrl', 'a')  # Select all

    print("Testing clicks...")
    time.sleep(1)
    sim.click()

    print("Done!")
