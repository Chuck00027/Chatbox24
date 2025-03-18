import tkinter as tk
import subprocess
import os
from tkinter import PhotoImage, messagebox

class ChatbotLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Program Launcher")
        self.root.geometry("600x500")  # 固定窗口大小
        self.root.resizable(False, False)  # 禁止调整大小

        self.setup_ui()

    def setup_ui(self):
        """初始化 GUI 组件"""
        if os.path.exists("logo.png"):
            self.img = PhotoImage(file="logo.png").subsample(3, 3)  # 缩小图片尺寸
            image_label = tk.Label(self.root, image=self.img)
            image_label.pack(pady=10)

        # 创建按钮框架
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Edit", width=15, command=lambda: self.run_script("GUI_load_MySQL.py")).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Work", width=15, command=lambda: self.run_script("GUI_work_MySQL.py")).grid(row=0, column=1, padx=5)
        tk.Button(button_frame, text="Training", width=15, command=lambda: self.run_script("GUI_training_MySQL.py")).grid(row=0, column=2, padx=5)
        tk.Button(button_frame, text="Testing", width=15, command=lambda: self.run_script("GUI_testing_MySQL.py")).grid(row=0, column=3, padx=5)

    def run_script(self, script_name):
        """运行外部 Python 脚本"""
        try:
            subprocess.Popen(['python', script_name], shell=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run {script_name}: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatbotLauncher(root)
    root.mainloop()
