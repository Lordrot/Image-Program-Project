import tkinter as tk
import subprocess

def run_script_1():
    subprocess.Popen(["env\\Scripts\\python", "Image_Screenshot.py"])

def run_script_2():
    subprocess.Popen(["env\\Scripts\\python", "Image_Alter.py"])

def run_script_3():
    subprocess.Popen(["env\\Scripts\\python", "Image_Shuffler.py"])

def run_script_4():
    subprocess.Popen(["env\\Scripts\\python", "Video_Capture.py"])

# def run_batch_file():
    # subprocess.Popen(["cmd", "/c", "D:\Img_Label\Run Label Studio.bat"])

def main():
    root = tk.Tk()
    root.title("Script Launcher")

    # Set the window size
    root.geometry("300x200")

    btn1 = tk.Button(root, text="Image_Screenshot", command=run_script_1)
    btn2 = tk.Button(root, text="Image_Alter", command=run_script_2)
    btn3 = tk.Button(root, text="Image_Shuffler", command=run_script_3)
    #btn4 = tk.Button(root, text="Label_Images", command=run_batch_file)
    btn5 = tk.Button(root, text="Video_Capture", command=run_script_4)
    

    btn1.pack(pady=10)
    btn2.pack(pady=10)
    btn3.pack(pady=10)
    #btn4.pack(pady=10)
    btn5.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
