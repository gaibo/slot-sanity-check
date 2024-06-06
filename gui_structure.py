import tkinter as tk
from contextlib import redirect_stdout
import io


"""
I'm sure there will be many times in my life where I want to generate a GUI 
text box with copy-paste capability to display text messages. This is one 
for the future.
"""


class Application:
    def __init__(self, root: tk.Tk, title: str = None) -> None:
        self.window = root
        if title:
            self.window.title(title)
        self.textbox = Textbox(self.window)


class Textbox:
    """ I definitely mean this to be a tk.Text-style text box class, but I'm not 
        sure about making it a direct subclass. At the moment, it seems nice to 
        group the tk.Frame/tk.Scrollbar creation all in here!
    """
    def __init__(self, master: tk.Misc) -> None:
        self.master = master    # tk.Misc includes both tk.Tk and tk.Widget; not sure if that'll be useful or confusing
        # Make a Frame
        self.frame = tk.Frame(
            master=self.master,
            borderwidth=3
        )
        self.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Make a Scrollbar in the Frame
        self.scrollbar = tk.Scrollbar(
            master=self.frame,
            orient='vertical'
        )
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
        # Make a Text (box) in the Frame, which uses the Frame's Scrollbar (convoluted?)
        self.text = tk.Text(
            master=self.frame,
            yscrollcommand=self.scrollbar.set
        )
        self.scrollbar.config(command=self.text.yview)  # Needed to make scrollbar clickable!
        self.text.pack(fill=tk.BOTH, expand=True)     # Fills and expands with Frame

        # Key bindings for convenience
        self.text.bind('<1>', lambda event: self.text.focus_set())  # Mouse button 1 allowed to set focus; need on OS X
        self.text.bind('<Key>', lambda event: 'break')  # Keys do nothing
        self.text.bind('<Control-Key-a>', lambda event: self.select_all())
        self.text.bind('<Control-Key-c>', lambda event: self.copy_selection())
        self.rightclickmenu = RightClickMenu(self)
        def popup_rightclickmenu(event):
            try:
                self.rightclickmenu.tk_popup(event.x_root, event.y_root)
            finally:
                self.rightclickmenu.grab_release()
        self.text.bind('<Button-3>', popup_rightclickmenu)  # Button-3 as right-click is platform-dependent...
    
    def print(self, message: str) -> None:
        self.text.insert(tk.END, message)
        self.text.see(tk.END)   # Scroll to the end

    def get_selection(self) -> str:
        if self.text.tag_ranges(tk.SEL):
            return self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
        else:
            return ''
    
    def copy_selection(self) -> None:
        # NOTE: It is a known issue with Tkinter that copying BUT CLOSING THE WINDOW BEFORE PASTING 
        #       causes the "copied" content to not actually reach the OS's clipboard. This has been 
        #       an open issue for literally a decade. I tried using alternative libraries, but 
        #       they didn't work either.
        #       So for now, I have no recommendation other than LEAVE THIS GUI WINDOW OPEN 
        #       WHILE YOU PASTE THE RESULT ELSEWHERE. Otherwise, paste won't work (and may even freeze).
        selected_str = self.get_selection()
        self.master.clipboard_clear()   # Any tk.Misc master should have these methods!
        self.master.clipboard_append(selected_str)  # pyperclip.copy(selected_str); xerox.copy(selected_str)
        self.master.update()    # Supposedly helps content reach clipboard before window is closed... not for me
    
    def highlight_all(self) -> None:
        # NOTE: This "highlights" with a color of my choice, but doesn't "select"!
        self.text.tag_add("highlight_all", '1.0', tk.END)
        self.text.tag_config("highlight_all", background='green', foreground='white')

    def select_all(self) -> None:
        self.text.tag_add(tk.SEL, '1.0', tk.END)
        self.text.mark_set(tk.INSERT, '1.0')
        self.text.see(tk.INSERT)
        return 'break'  # This is so idiosyncratic

    def copy_all(self) -> None:
        self.select_all()
        self.copy_selection()


class RightClickMenu(tk.Menu):
    """ I've tied the functionality of this class directly to Textbox - note 
        how a Textbox is the only argument needed to instantiate, because the 
        Menu-ness of this class sets Textbox.text as its master.
    """
    def __init__(self, textbox: Textbox, *args, master: tk.Widget = None, **kwargs) -> None:
        if master is None:
            master = textbox.text
        tk.Menu.__init__(self, master, *args, tearoff=0, **kwargs)
        # Note that Menu doesn't need to be packed
        self.textbox = textbox

        # Bindings
        def copy():
            self.textbox.copy_selection()
        def select_all_then_copy():
            self.textbox.copy_all()
        self.add_command(label='Copy', command=copy,
                         accelerator='Ctrl+C')  # Accelerator is literally just a string; binding was manual
        self.add_command(label='Select all, then copy', command=select_all_then_copy,
                         accelerator="Ctrl+A, Ctrl+C")


####

# Quick test script
if __name__ == '__main__':
    # Make root Tkinter object
    root = tk.Tk()

    # Create visuals in object-oriented manner around root
    app = Application(root, "My Window Title")
    # Test 1: Textbox class print method
    app.textbox.print("Testing, testing, testing of my Textbox's print method!\n" * 50)  # Fill up textbox to test scrollbar
    # Test 2: Using contextlib's redirect_stdout with traditional print function
    def _test_print():
        print("More testing, this time of contextlib's redirect_stdout!\n" * 25, end='')
    with redirect_stdout(io.StringIO()) as f:
        print()     # Explicit newline
        _test_print()
    captured_stdout_string = f.getvalue()  # Get the prints as a string
    app.textbox.print(captured_stdout_string)
    
    # Render with Tkinter event loop which keeps "window" open
    root.mainloop()
