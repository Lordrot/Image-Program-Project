import numpy as np
import win32gui, win32ui, win32con  # type: ignore
import ctypes
import cv2
from PIL import Image, ImageGrab
from time import sleep
import os
import tkinter as tk
from threading import Thread
from tkinter import messagebox
import ctypes

#This bit fixes DPI scaling issue which can occur with pixel offsets
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception as e:
    pass  # For Windows 8.1 and later


class WindowCapture:
    def __init__(self, window_name=None, delay=0.3, region=None):
        self.window_name = window_name
        self.delay = delay
        self.region = region  # Tuple: (left, top, right, bottom)
        self.running = False

        if self.window_name:
            # Initialize for window capture
            self.hwnd = win32gui.FindWindow(None, self.window_name)
            if not self.hwnd:
                raise Exception('Window not found: {}'.format(window_name))

            window_rect = win32gui.GetWindowRect(self.hwnd)
            self.w = window_rect[2] - window_rect[0]
            self.h = window_rect[3] - window_rect[1]

            border_pixels = 8
            titlebar_pixels = 30
            self.w = self.w - (border_pixels * 2)
            self.h = self.h - titlebar_pixels - border_pixels
            self.cropped_x = border_pixels
            self.cropped_y = titlebar_pixels
        elif self.region:
            # Initialize for region capture
            self.left, self.top, self.right, self.bottom = self.region
            self.w = self.right - self.left
            self.h = self.bottom - self.top
        else:
            raise Exception('Either window_name or region must be specified.')

    def get_screenshot(self):
        if self.window_name:
            return self._capture_window()
        elif self.region:
            return self._capture_screen_region()
        else:
            return None

    def _capture_window(self):
        hwnd_dc = None
        mfc_dc = None
        bitmap = None
        try:
            hwnd_dc = ctypes.windll.user32.GetDC(self.hwnd)
            mfc_dc = ctypes.windll.gdi32.CreateCompatibleDC(hwnd_dc)
            bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hwnd_dc, self.w, self.h)
            ctypes.windll.gdi32.SelectObject(mfc_dc, bitmap)
            ctypes.windll.gdi32.BitBlt(mfc_dc, 0, 0, self.w, self.h, hwnd_dc, self.cropped_x, self.cropped_y, 0x00CC0020)

            bmpstr = ctypes.create_string_buffer(self.w * self.h * 4)
            ctypes.windll.gdi32.GetBitmapBits(bitmap, len(bmpstr), bmpstr)
            img = np.frombuffer(bmpstr, dtype='uint8')
            img.shape = (self.h, self.w, 4)  # BGRA format

            # Clean up
            ctypes.windll.gdi32.DeleteObject(bitmap)
            ctypes.windll.gdi32.DeleteDC(mfc_dc)
            ctypes.windll.user32.ReleaseDC(self.hwnd, hwnd_dc)

            # Convert BGRA to RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
            return img

        except Exception as e:
            if bitmap:
                ctypes.windll.gdi32.DeleteObject(bitmap)
            if mfc_dc:
                ctypes.windll.gdi32.DeleteDC(mfc_dc)
            if hwnd_dc:
                ctypes.windll.user32.ReleaseDC(self.hwnd, hwnd_dc)
            print(f"Error capturing window: {e}")
            return None

    def _capture_screen_region(self):
        try:
            img = ImageGrab.grab(bbox=(self.left, self.top, self.right, self.bottom))
            img = np.array(img)
            return img
        except Exception as e:
            print(f"Error capturing screen region: {e}")
            return None

    def generate_image_dataset(self):
        if not os.path.exists("images"):
            os.mkdir("images")
        while self.running:
            img = self.get_screenshot()
            if img is not None:
                im = Image.fromarray(img)
                im.save(f"./images/img_{len(os.listdir('images'))}.jpg")
            else:
                print("Failed to capture screenshot.")
                break
            sleep(self.delay)

class ScreenshotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Screenshot Capture GUI")
        self.geometry("400x400")
        
        self.capture_mode = tk.StringVar(value="Window")

        # Radio buttons to select capture mode
        tk.Label(self, text="Select Capture Mode:").pack(pady=5)
        tk.Radiobutton(self, text="Window Capture", variable=self.capture_mode, value="Window").pack()
        tk.Radiobutton(self, text="Region Capture", variable=self.capture_mode, value="Region").pack()

        # Window name entry
        self.window_name_entry = tk.Entry(self)
        self.window_name_entry.pack(pady=10, padx=20)
        self.window_name_entry.insert(0, "YOUR_WINDOW_NAME_HERE")

        # Button to select region
        self.select_region_button = tk.Button(self, text="Select Region", command=self.select_screen_region, state=tk.DISABLED)
        self.select_region_button.pack(pady=5)

        self.region_label = tk.Label(self, text="Selected Region: None")
        self.region_label.pack()

        # Delay entry
        self.delay_label = tk.Label(self, text="Delay (seconds):")
        self.delay_label.pack()
        self.delay_entry = tk.Entry(self)
        self.delay_entry.pack(pady=5, padx=20)
        self.delay_entry.insert(0, "0.3")

        # Start and stop buttons
        self.start_button = tk.Button(self, text="Start Capturing", command=self.start_capturing)
        self.start_button.pack(pady=10, padx=10)
        self.stop_button = tk.Button(self, text="Stop Capturing", state=tk.DISABLED, command=self.stop_capturing)
        self.stop_button.pack(pady=10, padx=10)

        # Bind capture mode change
        self.capture_mode.trace('w', self.on_capture_mode_change) #trace was depreciated but it works trace_add doesn't work
        self.selected_region = None

    def on_capture_mode_change(self, *args):
        mode = self.capture_mode.get()
        if mode == "Window":
            self.window_name_entry.config(state=tk.NORMAL)
            self.select_region_button.config(state=tk.DISABLED)
        elif mode == "Region":
            self.window_name_entry.config(state=tk.DISABLED)
            self.select_region_button.config(state=tk.NORMAL)

    def start_capturing(self):
        delay_str = self.delay_entry.get()
        try:
            delay = float(delay_str)
        except ValueError:
            print("Invalid delay value. Please enter a number.")
            return

        mode = self.capture_mode.get()
        if mode == "Window":
            window_name = self.window_name_entry.get()
            if not window_name:
                print("Please enter a window name.")
                return
            try:
                self.wc = WindowCapture(window_name=window_name, delay=delay)
            except Exception as e:
                print(str(e))
                return
        elif mode == "Region":
            if not self.selected_region:
                print("Please select a region first.")
                return
            self.wc = WindowCapture(region=self.selected_region, delay=delay)
        else:
            print("Unknown capture mode.")
            return

        self.wc.running = True
        Thread(target=self.wc.generate_image_dataset).start()

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def stop_capturing(self):
        if hasattr(self, 'wc'):
            self.wc.running = False

        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def select_screen_region(self):
        messagebox.showinfo("Select Region", "Please click and drag to select the region.")

        # Hide the main window
        self.withdraw()

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
        self.deiconify()

if __name__ == "__main__":
    app = ScreenshotApp()
    app.mainloop()
