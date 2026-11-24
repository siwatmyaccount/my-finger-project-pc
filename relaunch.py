"""Full-screen "Back to the program" page.

Normally main.py draws this itself the moment the X button is pressed
(see AntiTriggerFingersApp.on_close), so it appears instantly while the
camera and AI threads finish in the background. Run on its own
(`python relaunch.py`) it is the launcher's fallback after a crash:
exit code 0 = start the program again, 1 = stop.
Plain tkinter only, so it costs nothing to draw.
"""
import os
import shutil
import sys
import tkinter as tk
from tkinter import font as tkfont
from pc_runtime import data_path

BASE_DIR = data_path()
PURPLE = "#4A235A"
GREEN = "#1E8449"
GREEN_LIGHT = "#2ECC71"
GREEN_DARK = "#145A32"
RING = "#A9DFBF"
RING_STEPS = ["#4A235A", "#5E3C6E", "#7A5A8A", "#96789F", "#B29AB8", "#CDBCD1", RING]


def prompt_family(root):
    """Use the bundled Prompt TH font if Tk can see it; install it to ~/.fonts otherwise."""
    if sys.platform == "win32":
        import ctypes
        for name in ("PromptTH-Bold.ttf", "PromptTH-Regular.ttf"):
            ctypes.windll.gdi32.AddFontResourceExW(os.path.join(BASE_DIR, "fonts", name), 0x10, 0)
        families = tkfont.families(root)
        return next((f for f in ("Prompt TH", "Sarabun", "Tahoma") if f in families), "TkDefaultFont")
    user_fonts = os.path.join(os.path.expanduser("~"), ".fonts")
    for name in ("PromptTH-Bold.ttf", "PromptTH-Regular.ttf"):
        source = os.path.join(BASE_DIR, "fonts", name)
        target = os.path.join(user_fonts, name)
        try:
            if os.path.exists(source) and not os.path.exists(target):
                os.makedirs(user_fonts, exist_ok=True)
                shutil.copyfile(source, target)
        except OSError:
            pass
    families = tkfont.families(root)
    for family in ("Prompt TH", "Prompt", "Sarabun", "Noto Sans Thai"):
        if family in families:
            return family
    return "TkDefaultFont"


def rounded(canvas, x1, y1, x2, y2, r, **kw):
    """Rounded rectangle on a canvas (one smoothed polygon)."""
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
              x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kw)


def make_fullscreen(window, width, height):
    """Cover the whole screen on X11 and on the Pi's Wayland desktop (labwc/wayfire).

    The fullscreen flag only sticks once the window is mapped, so it is set now
    and again shortly after; the explicit geometry covers compositors that
    ignore the flag for a moment.
    """
    window.geometry(f"{width}x{height}+0+0")

    def apply():
        try:
            window.attributes("-fullscreen", True)
        except tk.TclError:
            pass
        window.lift()
    apply()
    for delay in (60, 250, 700):
        window.after(delay, apply)


def build(window, on_back, on_quit, marks=lambda text: text):
    """Draw the page into `window` (a Tk root or a Toplevel).

    on_back() is called when the big button is tapped, on_quit() for Close.
    `marks` lets main.py pass its Thai tone-mark fixer for the Prompt TH font.
    Returns the function that stops the animation (call it before destroying).
    """
    sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
    window.configure(bg=PURPLE)
    make_fullscreen(window, sw, sh)
    family = prompt_family(window)

    canvas = tk.Canvas(window, bg=PURPLE, highlightthickness=0, bd=0, width=sw, height=sh)
    canvas.pack(fill="both", expand=True)

    head = max(26, min(48, sw // 26))
    canvas.create_text(sw // 2, int(sh * .14), text=marks("ปิดโปรแกรมแล้ว"), fill="#FFFFFF",
                       font=(family, head, "bold"))
    canvas.create_text(sw // 2, int(sh * .14) + head + 18, text="Program closed", fill="#D9C8E3",
                       font=(family, max(16, head * 2 // 3)))

    # One big rounded green button with a ring that "breathes": the only thing to tap.
    bw, bh = int(sw * .72), int(sh * .34)
    bx1, by1 = (sw - bw) // 2, int(sh * .32)
    bx2, by2 = bx1 + bw, by1 + bh
    ring = rounded(canvas, bx1 - 14, by1 - 14, bx2 + 14, by2 + 14, 46, fill="", outline=RING, width=6)
    shadow = rounded(canvas, bx1 + 6, by1 + 10, bx2 + 6, by2 + 10, 40, fill="#2E1538", outline="")
    body = rounded(canvas, bx1, by1, bx2, by2, 40, fill=GREEN, outline=GREEN_LIGHT, width=4)
    big = max(30, min(64, bw // 14))
    label_th = canvas.create_text(sw // 2, by1 + bh * .40, text=marks("ย้อนกลับเข้าโปรแกรม"), fill="#FFFFFF",
                                  font=(family, big, "bold"))
    label_en = canvas.create_text(sw // 2, by1 + bh * .70, text="Back to the program", fill="#E9F7EF",
                                  font=(family, max(20, big * 2 // 3), "bold"))
    state = {"done": False}

    def pressed(event=None):
        canvas.itemconfigure(body, fill=GREEN_DARK)
        canvas.itemconfigure(label_th, text=marks("กำลังเปิดโปรแกรม..."))
        canvas.itemconfigure(label_en, text="Opening...")

    def released(event=None):
        if state["done"]:
            return
        state["done"] = True
        pressed()
        on_back()

    for item in (shadow, body, label_th, label_en):
        canvas.tag_bind(item, "<ButtonPress-1>", pressed)
        canvas.tag_bind(item, "<ButtonRelease-1>", released)

    hint = canvas.create_text(sw // 2, by2 + int(sh * .07), text=marks("แตะปุ่มสีเขียวเพื่อใช้งานต่อ"),
                              fill="#FFFFFF", font=(family, max(18, head * 3 // 5)))
    canvas.create_text(sw // 2, by2 + int(sh * .07) + head, text="Tap the green button to continue",
                       fill="#D9C8E3", font=(family, max(14, head // 2)))

    close_btn = tk.Button(window, text=marks("ปิด / Close"), command=on_quit, bg="#68417A", fg="#FFFFFF",
                          activebackground="#84579B", activeforeground="#FFFFFF", relief="flat", bd=0,
                          font=(family, max(14, head // 2)), padx=30, pady=8, highlightthickness=0,
                          cursor="hand2")
    close_btn.place(relx=.5, rely=.95, anchor="s")

    frame = {"i": 0, "dir": 1, "job": None}

    def breathe():
        if state.get("stopped"):
            return
        frame["i"] += frame["dir"]
        if frame["i"] in (0, len(RING_STEPS) - 1):
            frame["dir"] *= -1
        try:
            canvas.itemconfigure(ring, outline=RING_STEPS[frame["i"]])
            canvas.itemconfigure(hint, fill="#FFFFFF" if frame["i"] > 2 else "#D9C8E3")
            frame["job"] = window.after(110, breathe)
        except tk.TclError:
            pass

    frame["job"] = window.after(200, breathe)
    window.bind("<Escape>", lambda e: on_quit())
    window.bind("<Return>", released)
    window.after(250, window.focus_force)

    def stop():
        state["stopped"] = True
        if frame["job"] is not None:
            try:
                window.after_cancel(frame["job"])
            except tk.TclError:
                pass
    return stop


def main():
    root = tk.Tk()
    root.title("Finger Exercise Coach")
    result = {"code": 1}

    def back():
        result["code"] = 0
        root.after(150, root.destroy)

    def quit_():
        result["code"] = 1
        root.destroy()

    build(root, back, quit_)
    root.protocol("WM_DELETE_WINDOW", quit_)
    root.mainloop()
    sys.exit(result["code"])


if __name__ == "__main__":
    main()
