import tkinter as tk
import subprocess
import os
from tkinter import PhotoImage

def run_script(script_name):
    """
    Run an external Python script.
    :param script_name: The name of the Python script to execute.
    """
    try:
        subprocess.Popen(['python', script_name], shell=False)
    except Exception as e:
        tk.messagebox.showerror("Error", f"Failed to run {script_name}: {e}")

def create_main_gui():
    """
    Create the main graphical user interface (GUI) for the program launcher.
    """
    root = tk.Tk()
    root.title("Program Launcher")
    root.geometry("600x500")  # Fixed window size
    root.resizable(False, False)  # Disable window resizing

    # Add an image to the GUI (resized to fit better)
    img = PhotoImage(file="logo.png")
    img = img.subsample(3, 3)  # Resize image to two-thirds
    image_label = tk.Label(root, image=img)
    image_label.pack(pady=10)

    # Add buttons to launch different scripts in a single row
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    tk.Button(button_frame, text="Edit", width=15, command=lambda: run_script("loadfile.py")).grid(row=0, column=0, padx=5)
    tk.Button(button_frame, text="Work", width=15, command=lambda: run_script("GUI_multi.py")).grid(row=0, column=1, padx=5)
    tk.Button(button_frame, text="Training", width=15, command=lambda: run_script("GUI_training.py")).grid(row=0, column=2, padx=5)
    tk.Button(button_frame, text="Testing", width=15, command=lambda: run_script("GUI_testing.py")).grid(row=0, column=3, padx=5)

    root.mainloop()

if __name__ == "__main__":
    create_main_gui()
