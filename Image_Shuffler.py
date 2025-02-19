import os
import random
import shutil
from tkinter import Tk, Button, Label, filedialog

class LabelUtils:
    def __init__(self, source_folder, shuffled_folder):
        self.source_folder = source_folder
        self.shuffled_folder = shuffled_folder

    def create_shuffled_images_folder(self):
        if not os.path.exists(self.shuffled_folder):
            os.mkdir(self.shuffled_folder)

        image_files = [f for f in os.listdir(self.source_folder) if f.endswith(".jpg")]
        random.shuffle(image_files)

        for img in image_files:
            shutil.move(os.path.join(self.source_folder, img), 
                        os.path.join(self.shuffled_folder, f"img_{len(os.listdir(self.shuffled_folder))}.jpg"))

class ImageShufflerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Shuffler")

        # Set the window size
        root.geometry("300x150")

        self.label = Label(root, text="Choose the folder with images to shuffle:")
        self.label.pack(pady=10)

        self.select_button = Button(root, text="Select Folder", command=self.select_folder)
        self.select_button.pack(pady=5)

        self.shuffle_button = Button(root, text="Shuffle Images", command=self.shuffle_images, state='disabled')
        self.shuffle_button.pack(pady=5)

        self.source_folder = None

    def select_folder(self):
        self.source_folder = filedialog.askdirectory()
        if self.source_folder:
            self.label.config(text=f"Selected Folder: {self.source_folder}")
            self.shuffle_button.config(state='normal')

    def shuffle_images(self):
        shuffled_folder = os.path.join(self.source_folder, "shuffled_images")
        lbUtils = LabelUtils(self.source_folder, shuffled_folder)
        lbUtils.create_shuffled_images_folder()
        self.label.config(text="Images have been shuffled!")

if __name__ == "__main__":
    root = Tk()
    app = ImageShufflerApp(root)
    root.mainloop()