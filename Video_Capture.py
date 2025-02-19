import tkinter as tk
from tkinter import messagebox
import cv2
import PIL.Image, PIL.ImageTk
import numpy as np
from ultralytics import YOLO
import threading
import ctypes
from PIL import ImageGrab
from ctypes import wintypes
from tkinter import filedialog

#This bit fixes DPI scaling issue which can occur with pixel offsets
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception as e:
    pass  # For Windows 8.1 and later

user32 = ctypes.windll.user32

# Function to enumerate all open windows
def enum_windows():
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    GetWindowText = user32.GetWindowTextW
    GetWindowTextLength = user32.GetWindowTextLengthW
    IsWindowVisible = user32.IsWindowVisible

    titles = []

    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                titles.append((buff.value, hwnd))
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return titles

class MyVideoCapture:
    def __init__(self, source_type, source):
        self.source_type = source_type
        self.source = source

        if self.source_type == 'window_name':
            self.hwnd = ctypes.windll.user32.FindWindowW(None, self.source)
            if not self.hwnd:
                raise Exception(f'Window "{self.source}" not found!')

            # Get window client area size
            rect = wintypes.RECT()
            ctypes.windll.user32.GetClientRect(self.hwnd, ctypes.byref(rect))
            self.width = rect.right - rect.left
            self.height = rect.bottom - rect.top

        elif self.source_type == 'window_list':
            self.hwnd = self.source

            # Get window client area size
            rect = wintypes.RECT()
            ctypes.windll.user32.GetClientRect(self.hwnd, ctypes.byref(rect))
            self.width = rect.right - rect.left
            self.height = rect.bottom - rect.top

        elif self.source_type == 'screen_region':
            self.left, self.top, self.right, self.bottom = self.source
            self.width = self.right - self.left
            self.height = self.bottom - self.top

    def get_frame(self):
        if self.source_type in ['window_name', 'window_list']:
            return self._capture_window()
        elif self.source_type == 'screen_region':
            return self._capture_screen_region()

    def _capture_window(self):
        hwnd_dc = None
        mfc_dc = None
        bitmap = None
        try:
            hwnd_dc = ctypes.windll.user32.GetDC(self.hwnd)
            mfc_dc = ctypes.windll.gdi32.CreateCompatibleDC(hwnd_dc)
            bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hwnd_dc, self.width, self.height)
            ctypes.windll.gdi32.SelectObject(mfc_dc, bitmap)
            ctypes.windll.gdi32.BitBlt(mfc_dc, 0, 0, self.width, self.height, hwnd_dc, 0, 0, 0x00CC0020)

            bmpstr = ctypes.create_string_buffer(self.width * self.height * 4)
            ctypes.windll.gdi32.GetBitmapBits(bitmap, len(bmpstr), bmpstr)
            img = np.frombuffer(bmpstr, dtype='uint8').reshape((self.height, self.width, 4))  # BGRA format

            ctypes.windll.gdi32.DeleteObject(bitmap)
            ctypes.windll.gdi32.DeleteDC(mfc_dc)
            ctypes.windll.user32.ReleaseDC(self.hwnd, hwnd_dc)

            # Convert BGRA to RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
            return True, img

        except Exception as e:
            if bitmap:
                ctypes.windll.gdi32.DeleteObject(bitmap)
            if mfc_dc:
                ctypes.windll.gdi32.DeleteDC(mfc_dc)
            if hwnd_dc:
                ctypes.windll.user32.ReleaseDC(self.hwnd, hwnd_dc)
            print(f"Error capturing window: {e}")
            return False, None

    def _capture_screen_region(self):
        try:
            img = ImageGrab.grab(bbox=(self.left, self.top, self.right, self.bottom))
            img = np.array(img)
            return True, img
        except Exception as e:
            print(f"Error capturing screen region: {e}")
            return False, None

class App:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.yolo_enabled = False
        self.model = None

        # Set the initial window size
        self.window.geometry("500x250")  # Adjusted size

        # Capture method selection
        self.capture_method = tk.StringVar(value='window_name')

        self.method_label = tk.Label(window, text="Select Capture Method:")
        self.method_label.grid(row=0, column=2)

        self.radio_window_name = tk.Radiobutton(window, text="Enter Window Name", variable=self.capture_method, value='window_name', command=self.update_input_fields)
        self.radio_window_name.grid(row=1, column=1)

        self.radio_window_list = tk.Radiobutton(window, text="Choose from Open Windows", variable=self.capture_method, value='window_list', command=self.update_input_fields)
        self.radio_window_list.grid(row=1, column=2)

        self.radio_screen_region = tk.Radiobutton(window, text="Select Screen Region", variable=self.capture_method, value='screen_region', command=self.update_input_fields)
        self.radio_screen_region.grid(row=1, column=3)

        # Input fields for window name
        self.window_name_label = tk.Label(window, text="Enter Window Name:")
        self.window_name_entry = tk.Entry(window)

        # Dropdown for open windows
        self.open_windows = []
        self.window_list_var = tk.StringVar()
        self.window_list_dropdown = tk.OptionMenu(window, self.window_list_var, ())

        self.refresh_button = tk.Button(window, text="Refresh Window List", command=self.refresh_window_list)

        # Button for selecting screen region
        self.select_region_button = tk.Button(window, text="Select Region", command=self.select_screen_region)
        self.region_label = tk.Label(window, text="Selected Region: None")
        self.selected_region = None

        # Start and Stop buttons
        self.start_button = tk.Button(window, text="Start", command=self.start_capture)
        self.stop_button = tk.Button(window, text="Stop", command=self.stop_capture, state=tk.DISABLED)

        # Slider to adjust frame rate
        self.slider_label = tk.Label(window, text="Adjust Frame Rate:")
        self.slider = tk.Scale(window, from_=1, to=30, orient=tk.HORIZONTAL)
        self.slider.set(15)  # Set initial frame rate

        # Checkbox to enable/disable YOLO, alongside the load button
        self.yolo_var = tk.IntVar()
        self.yolo_checkbox = tk.Checkbutton(window, text="Enable YOLO", variable=self.yolo_var, command=self.toggle_yolo)
        self.load_button = tk.Button(window, text="Load YOLO Model", command=self.start_loading_yolo_model)
        
        self.canvas = None  # Initialize canvas as None
        self.vid = None    # VideoCapture object will be created later

        # Set initial delay time in milliseconds
        self.delay = 1000 // self.slider.get()

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close event

        self.update_input_fields()  # Initialize input fields based on default capture method
        self.window.mainloop()

    def start_loading_yolo_model(self):
        # Load YOLO model in a separate thread to prevent GUI freezing
        threading.Thread(target=self.load_yolo_model).start()

    def load_yolo_model(self):
        try:
            # Open a file dialog and allow the user to select a file
            model_path = filedialog.askopenfilename(
                title="Select File",
                filetypes=(("Yolo Model", "*.pt*"), ("All files", "*.*")))
            
            if not model_path:
                messagebox.showwarning("No File Selected", "No YOLO model file was selected.")
                return
            
            self.model = YOLO(model_path)
            print(f"YOLO model loaded: {model_path}")
            messagebox.showinfo("Success", f"YOLO model loaded: {model_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load YOLO model: {e}")

    def toggle_yolo(self):
        self.yolo_enabled = bool(self.yolo_var.get())
        print(f"YOLO enabled: {self.yolo_enabled}")
        if not self.model and self.yolo_enabled:
            messagebox.showwarning("Model Not Loaded", "YOLO model is not loaded. Please load the model first.")

    def on_closing(self):
        if self.vid:
            self.vid = None
        print("Application is closing.")
        self.window.destroy()

    def update_input_fields(self):
        method = self.capture_method.get()

        # Clear existing input fields
        for widget in self.window.grid_slaves():
            widget.grid_forget()

        # Grid common widgets
        self.method_label.grid(row=0, column=2)
        self.radio_window_name.grid(row=1, column=1)
        self.radio_window_list.grid(row=1, column=2)
        self.radio_screen_region.grid(row=1, column=3)

        if method == 'window_name':
            self.window_name_label.grid(row=2, column=2, padx=10, pady=5)
            self.window_name_entry.grid(row=3, column=2, padx=10, pady=5)
        elif method == 'window_list':
            self.refresh_window_list()
            self.window_list_dropdown.grid(row=3, column=2, padx=10, pady=5)
            self.refresh_button.grid(row=2, column=2, padx=10, pady=5)
        elif method == 'screen_region':
            self.select_region_button.grid(row=2, column=2, padx=10, pady=5)
            self.region_label.grid(row=3, column=2, padx=10, pady=5)

        # Grid the rest of the widgets
        self.start_button.grid(row=4, column=1, padx=10, pady=5)
        self.load_button.grid(row=4, column=2, padx=10, pady=5)
        self.stop_button.grid(row=4, column=3, padx=10, pady=5)
        self.slider_label.grid(row=5, column=1, padx=10, pady=5)
        self.slider.grid(row=5, column=2)
        self.yolo_checkbox.grid(row=5, column=3, padx=10, pady=5)
        

    def refresh_window_list(self):
        self.open_windows = enum_windows()
        window_titles = [title for title, hwnd in self.open_windows]

        # Update the OptionMenu with new titles
        menu = self.window_list_dropdown["menu"]
        menu.delete(0, "end")
        for title in window_titles:
            menu.add_command(label=title, command=lambda value=title: self.window_list_var.set(value))
        if window_titles:
            self.window_list_var.set(window_titles[0])
        else:
            self.window_list_var.set('No windows found')
        print("Window list refreshed.")

    def select_screen_region(self):
        messagebox.showinfo("Select Region", "Please click and drag to select the region.")

        # Hide the main window
        self.window.withdraw()

        # Create a full-screen transparent window
        self.selection_window = tk.Toplevel()
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-alpha', 0.3)
        self.selection_window.config(bg='gray')
        self.selection_window.lift()
        self.selection_window.attributes("-topmost", True)
        self.selection_window.bind("<ButtonPress-1>", self.on_button_press)
        self.selection_window.bind("<B1-Motion>", self.on_move_press)
        self.selection_window.bind("<ButtonRelease-1>", self.on_button_release)

        self.start_x = None
        self.start_y = None
        self.rect = None
        self.canvas_widget = tk.Canvas(self.selection_window, bg='gray', highlightthickness=0)
        self.canvas_widget.pack(fill=tk.BOTH, expand=tk.YES)

    def on_button_press(self, event):
        self.start_x = self.selection_window.winfo_pointerx()
        self.start_y = self.selection_window.winfo_pointery()
        self.rect = self.canvas_widget.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red')

    def on_move_press(self, event):
        cur_x = self.selection_window.winfo_pointerx()
        cur_y = self.selection_window.winfo_pointery()
        self.canvas_widget.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x = self.selection_window.winfo_pointerx()
        end_y = self.selection_window.winfo_pointery()

        self.selected_region = (
            min(self.start_x, end_x),
            min(self.start_y, end_y),
            max(self.start_x, end_x),
            max(self.start_y, end_y)
        )

        self.region_label.config(text=f"Selected Region: {self.selected_region}")

        self.canvas_widget.destroy()
        self.selection_window.destroy()
        self.window.deiconify()

    def start_capture(self):
        print("Start capturing.")
        method = self.capture_method.get()

        if method == 'window_name':
            window_name = self.window_name_entry.get().strip()
            if not window_name:
                messagebox.showwarning("Input Error", "Please enter a valid window name.")
                return
            source = window_name

        elif method == 'window_list':
            selected_title = self.window_list_var.get()
            if not selected_title or selected_title == 'No windows found':
                messagebox.showwarning("Input Error", "Please select a valid window.")
                return
            hwnd = None
            for title, handle in self.open_windows:
                if title == selected_title:
                    hwnd = handle
                    break
            if not hwnd:
                messagebox.showerror("Error", f'Window "{selected_title}" not found!')
                print(f"Error starting capture: Window not found.")
                return
            source = hwnd

        elif method == 'screen_region':
            if not self.selected_region:
                messagebox.showwarning("Input Error", "Please select a screen region.")
                return
            source = self.selected_region  # (left, top, right, bottom)

        else:
            messagebox.showerror("Error", "Invalid capture method.")
            return

        try:
            self.vid = MyVideoCapture(method, source)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            print(f"Error starting capture: {e}")
            return

        # Adjust the window size based on the captured frame dimensions
        extra_width = 1
        extra_height = 203
        self.window.geometry(f"{self.vid.width + extra_width}x{self.vid.height + extra_height}")
        #self.window.geometry(f"{self.vid.width}x{self.vid.height}")
        
        # Create or update canvas
        if self.canvas is None:
            self.canvas = tk.Canvas(self.window, width=self.vid.width, height=self.vid.height)
            self.canvas.grid(column=1,columnspan=3, row=6)
        else:
            self.canvas.config(width=self.vid.width, height=self.vid.height)

        # Enable stop button and disable start button
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Start the update loop
        self.update()

    def stop_capture(self):
        print("Stop capturing.")
        if self.vid:
            self.vid = None

        # Disable stop button and enable start button
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def update(self):
        try:
            ret = False  # Initialize ret as False
            frame = None  # Initialize frame as None

            if self.vid is not None:
                ret, frame = self.vid.get_frame()

                if ret:
                    if self.yolo_enabled and hasattr(self, 'model'):
                        results = self.model(frame)
                        annotated_frame = results[0].plot()
                        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(annotated_frame))
                    else:
                        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
                    self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

            # Adjust delay based on the slider value
            self.delay = 1000 // self.slider.get()

            # Schedule the `update` method to be called after a delay
            if self.vid is not None:  # Continue updating only if capturing
                self.window.after(self.delay, self.update)
        except Exception as e:
            print(f"Error in update loop: {e}")
            self.stop_capture()

if __name__ == "__main__":
    App(tk.Tk(), "Flexible Capture with YOLO")
