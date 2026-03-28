import os
import subprocess
import threading
import json
from tkinter import filedialog, messagebox
import requests
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO
import customtkinter as ctk
import yt_dlp
import pystray
import sys


if hasattr(sys, 'frozen'):
    os.chdir(os.path.dirname(sys.executable))


# ---------------- GLOBALS ----------------
downloaded_file = None
is_downloading = False
stop_download = False

# ---------------- CONFIG ----------------
CONFIG_FILE = "config.json"

def load_config():
    default_config = {"download_path": os.path.join(os.path.expanduser("~"), "Downloads")}
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f)
        return default_config
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            for key, val in default_config.items():
                if key not in data:
                    data[key] = val
            return data
    except:
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f)
        return default_config

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

config = load_config()

# ---------------- APP ----------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("500x400")
app.title("Ultimate Video Downloader")
app.resizable(False, False)

# ---------------- EXIT HANDLER (MINIMIZE TO TRAY) ----------------
def create_tray_icon():
    image = Image.new('RGB', (64, 64), color='blue')
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill='white')
    return image

def on_tray_quit(icon, item):
    global stop_download
    stop_download = True  # stop active downloads if running
    icon.stop()           # stop tray icon
    app.after(0, app.destroy)  # safely close tkinter
    sys.exit()

def on_tray_open(icon, item):
    icon.stop()
    app.deiconify()

def show_tray_icon():
    icon = pystray.Icon(
        "Video Downloader",
        create_tray_icon(),
        "Video Downloader",
        menu=pystray.Menu(
            pystray.MenuItem("Open", on_tray_open, default=True),
            pystray.MenuItem("Exit", on_tray_quit)
        )
    )
    icon.run()

def on_app_close():
    app.withdraw()
    threading.Thread(target=show_tray_icon, daemon=True).start()
    print("App minimized to tray.")

app.protocol("WM_DELETE_WINDOW", on_app_close)

# ---------------- FRAMES ----------------
home_frame = ctk.CTkFrame(app)
download_frame = ctk.CTkFrame(app)
home_frame.pack(fill="both", expand=True)

# ---------------- HOME FRAME ----------------
title = ctk.CTkLabel(home_frame, text="Ultimate Video Downloader", font=("Arial",26))
title.pack(pady=20)

buttons_frame = ctk.CTkFrame(home_frame)
buttons_frame.pack(pady=20)

download_mode = ctk.StringVar()

def show_download(mode):
    reset_ui()
    download_mode.set(mode)
    home_frame.pack_forget()
    download_frame.pack(fill="both", expand=True)

ctk.CTkButton(buttons_frame,text="Download Best Video + Audio", width=300, command=lambda:show_download("bestvideo+bestaudio")).pack(pady=6)
ctk.CTkButton(buttons_frame,text="Download Video Only", width=300, command=lambda:show_download("bestvideo")).pack(pady=6)
ctk.CTkButton(buttons_frame,text="Download Audio Only", width=300, command=lambda:show_download("bestaudio")).pack(pady=6)
ctk.CTkButton(buttons_frame,text="Change Download Location", width=300, command=lambda: change_location()).pack(pady=6)

location_label = ctk.CTkLabel(home_frame,text=config["download_path"])
location_label.pack(pady=10)

ctk.CTkButton(home_frame, text="Exit", command=on_app_close).pack(pady=10)

# ---------------- DOWNLOAD FRAME ----------------
top_bar = ctk.CTkFrame(download_frame)
top_bar.pack(fill="x")
ctk.CTkButton(top_bar, text="⬅ Back", command=lambda: go_home()).pack(side="left", padx=10, pady=10)

url_entry = ctk.CTkEntry(download_frame,width=500, placeholder_text="Paste video URL")
url_entry.pack(pady=10)

progress_bar = ctk.CTkProgressBar(download_frame,width=400)
progress_label = ctk.CTkLabel(download_frame,text="")
navigate_button = ctk.CTkButton(download_frame,text="Navigate To File",command=lambda: open_file())

# ---------------- FUNCTIONS ----------------
def reset_ui():
    url_entry.delete(0, "end")
    progress_bar.pack_forget()
    progress_label.configure(text="")
    navigate_button.pack_forget()

def go_home():
    global stop_download
    if is_downloading:
        confirm = messagebox.askyesno("Exit Download","Download is running. Exit anyway?")
        if confirm:
            stop_download = True
        else:
            return
    reset_ui()
    download_frame.pack_forget()
    home_frame.pack(fill="both", expand=True)

def change_location():
    folder = filedialog.askdirectory()
    if folder:
        config["download_path"] = folder
        save_config()
        location_label.configure(text=folder)

def open_file():
    if downloaded_file and os.path.exists(downloaded_file):
        if os.name == "nt":
            subprocess.Popen(f'explorer /select,"{downloaded_file}"')
        else:
            subprocess.Popen(["xdg-open",downloaded_file])

def progress_hook(d):
    global stop_download
    if stop_download:
        raise Exception("Download stopped by user")
    if d["status"] == "downloading":
        percent = d.get("_percent_str","0").replace("%","")
        speed = d.get("_speed_str","")
        eta = d.get("_eta_str","")
        progress_bar.set(float(percent)/100)
        progress_label.configure(text=f"{percent}% | {speed} | ETA {eta}")
    if d["status"] == "finished":
        progress_bar.pack_forget()
        progress_label.configure(text="Download Complete")
        navigate_button.pack(pady=10)

def download():
    global downloaded_file, is_downloading, stop_download
    url = url_entry.get()
    if not url:
        return
    progress_bar.pack(pady=10)
    progress_label.pack()
    navigate_button.pack_forget()
    is_downloading = True
    stop_download = False

    def task():
        global downloaded_file, is_downloading
        try:
            outtmpl = os.path.join(config["download_path"],"%(title)s.%(ext)s")
            ydl_opts = {
                "format": download_mode.get(),
                "merge_output_format": "mp4",
                "progress_hooks": [progress_hook],
                "outtmpl": outtmpl,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    progress_label.configure(text="File already exists.")
                    progress_bar.pack_forget()
                    return
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
        except Exception as e:
            progress_label.configure(text=str(e))
        is_downloading = False

    threading.Thread(target=task).start()

def download_thumbnail():
    url = url_entry.get()
    if not url:
        return

    def task():
        try:
            with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                info = ydl.extract_info(url, download=False)

            thumb = info["thumbnails"][-1]["url"]
            data = requests.get(thumb).content

            name = info["title"] + ".jpg"
            path = os.path.join(config["download_path"], name)

            with open(path,"wb") as f:
                f.write(data)

            progress_label.pack()
            progress_label.configure(text="Thumbnail downloaded")

        except:
            progress_label.pack()
            progress_label.configure(text="Thumbnail download failed")

    threading.Thread(target=task).start()

# ---------------- DOWNLOAD FRAME BUTTONS ----------------
ctk.CTkButton(download_frame,text="Download",command=download).pack(pady=5)
ctk.CTkButton(download_frame,text="Download Thumbnail",command=download_thumbnail).pack(pady=5)

# ---------------- START APP ----------------
# Start minimized to tray
app.withdraw()
threading.Thread(target=show_tray_icon, daemon=True).start()

app.mainloop()