import os
from PIL import Image
import torchvision.transforms as transforms
import tkinter as tk
from tkinter import filedialog
import random

### Define the ImageDataset class to handle image loading and transformations
class ImageDataset:
    def __init__(self, file_list, transform=None):
        self.file_list = file_list
        self.transform = transform

    def __len__(self):
        return len(self.file_list)

    def __getitem__(self, idx):
        img_path = self.file_list[idx]
        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, img_path

### Define the transformation pipelines without resizing
def random_color_jitter():
    brightness = random.uniform(0.1, 0.3)
    contrast = random.uniform(0.1, 0.3)
    saturation = random.uniform(0.1, 0.3)
    return transforms.ColorJitter(brightness=brightness, contrast=contrast, saturation=saturation)

def get_transform(pipeline_type):
    if pipeline_type == "original":
        return transforms.Compose([
            transforms.RandomResizedCrop([178, 178]),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor()
        ])
    elif pipeline_type == "color_manipulation":
        return transforms.Compose([
            transforms.RandomResizedCrop([178, 178]),
            transforms.RandomHorizontalFlip(),
            random_color_jitter(),
            transforms.ToTensor()
        ])
    else:
        raise ValueError("Invalid pipeline type")

### Function to perform data augmentation
def augment_images(input_folder, output_folder, transform, num_samples):
    # Collect all image file paths in the input folder
    file_list = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    # Ensure we have enough images to sample from
    if num_samples > len(file_list):
        raise ValueError(f"Not enough images in the input folder ({len(file_list)}). Cannot generate {num_samples} samples.")
    
    # Randomly sample image paths
    sampled_paths = random.sample(file_list, num_samples)
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    dataset = ImageDataset(sampled_paths, transform=transform)
    
    # Perform transformations and save augmented images
    for i in range(len(dataset)):
        img_tensor, original_img_path = dataset[i]
        transformed_img = transforms.ToPILImage()(img_tensor)
        
        # Resize the transformed image to match the original image size
        with Image.open(original_img_path) as img:
            original_size = img.size
        
        resized_transformed_img = transformed_img.resize(original_size, Image.Resampling.LANCZOS)

        # Save the augmented image
        output_file_path = os.path.join(output_folder, f'augmented_{i}.jpg')
        resized_transformed_img.save(output_file_path)

### Function to browse folders using Tkinter filedialog
def browse_folder(entry):
    folder_path = filedialog.askdirectory()
    entry.delete(0, tk.END)
    entry.insert(0, folder_path)

### Function to run the augmentation process
def run_augmentation():
    input_folder = input_entry.get()
    output_folder = output_entry.get()
    pipeline_type = transform_var.get()
    num_samples = int(num_samples_entry.get())
    
    if not os.path.exists(input_folder):
        result_label.config(text="Input folder does not exist!", fg='red')
        return
    
    try:
        transform = get_transform(pipeline_type)
        augment_images(input_folder, output_folder, transform, num_samples)
        result_label.config(text="Augmentation completed successfully!", fg='green')
    except ValueError as e:
        result_label.config(text=str(e), fg='red')

### Create the main window
root = tk.Tk()
root.title("Image Data Augmentation")

# Input folder selection
tk.Label(root, text="Input Folder:").grid(row=0, column=0, padx=10, pady=5)
input_entry = tk.Entry(root, width=50)
input_entry.grid(row=0, column=1, padx=10, pady=5)
browse_input_button = tk.Button(root, text="Browse", command=lambda: browse_folder(input_entry))
browse_input_button.grid(row=0, column=2, padx=10, pady=5)

# Output folder selection
tk.Label(root, text="Output Folder:").grid(row=1, column=0, padx=10, pady=5)
output_entry = tk.Entry(root, width=50)
output_entry.grid(row=1, column=1, padx=10, pady=5)
browse_output_button = tk.Button(root, text="Browse", command=lambda: browse_folder(output_entry))
browse_output_button.grid(row=1, column=2, padx=10, pady=5)

# Transformation pipeline selection
tk.Label(root, text="Transformation Pipeline:").grid(row=2, column=0, padx=10, pady=5)
transform_var = tk.StringVar(value="original")
pipeline_options = ["original", "color_manipulation"]
for i, option in enumerate(pipeline_options):
    tk.Radiobutton(root, text=option, variable=transform_var, value=option).grid(row=2, column=i+1)

# Number of samples entry
tk.Label(root, text="Number of Samples:").grid(row=3, column=0, padx=10, pady=5)
num_samples_entry = tk.Entry(root, width=50)
num_samples_entry.grid(row=3, column=1, padx=10, pady=5)

# Run augmentation button
run_button = tk.Button(root, text="Run Augmentation", command=run_augmentation)
run_button.grid(row=4, column=0, columnspan=3, pady=20)

# Result label
result_label = tk.Label(root, text="")
result_label.grid(row=5, column=0, columnspan=3)

root.mainloop()