try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from logging import root
from PIL import Image, ImageTk
import customtkinter as ctk
import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

import pygame
import time, threading
from datetime import datetime, timedelta
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from collections import defaultdict
import sys, os
import tkinter as tk
from tkinter import ttk
import random
import math
import numpy as np

def resource_path(*parts):
    """Return an asset path that works from source and a PyInstaller bundle."""
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, *parts)

class AntiTriggerFingersApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        
        base_w = 1920
        base_h = 1080

        self.scale_w = self.screen_width / base_w
        self.scale_h = self.screen_height / base_h
        self.u_scale = min(self.scale_w, self.scale_h)

        self.title("AI-Powered Anti-trigger Fingers")
        self.bind("<Escape>", lambda e: self.on_close())
        self.configure(fg_color="#F4F7F6") 

        self.target_sets_var = tk.IntVar(value=3)

        self.key_held = False
        self.time_max = 5
        self.time_current = self.time_max
        self.hand_posit = 0
        self.still_hold = False
        self.current_pose = 1
        self.key = ""
        self.is_pass = False
        self.round = 0
        self.set = 0
        self.streak_days = 0
        
        self.chart_timeframe = 14
        
        # --- ตัวแปรสำหรับ Cache กราฟ ---
        self._cached_history_data = None
        self._last_history_read_time = 0

        self.pose_name = [
            "placeholder",
            "เหยียดมือตรง",
            "ทำมือคล้ายตะขอ",
            "กำมือ",
            "กำมือแบบเหยียดปลายนิ้ว",
            "งอโคนนิ้วแต่เหยียดปลายนิ้วมือ" 
        ]

        # --- แก้ไขการสแกนหากล้อง (เสียบ USB จะได้ใช้ตัวนั้น) ---
        self.cap = None
        for i in range(3, -1, -1): 
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                self.cap = cap
                print(f"Webcam opened successfully at index {i} via DirectShow!")
                break
        
        if self.cap is None or not self.cap.isOpened():
            print("Error: Cannot open any webcam")
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 

        # --- UI Colors ---
        self.purple_bg = "#4A235A" 
        self.light_gray_bg = "#FFFFFF" 
        self.light_gray_bg_program = "transparent"
        self.red_btn = "#E74C3C"
        self.hover_red_bt = "#C0392B"
        self.yellow_btn = "#F39C12"
        self.hover_yellow_bt = "#D68910"
        self.green_btn = "#2ECC71"
        self.hover_green_bt = "#27AE60"
        self.blue_btn = "#3498DB"
        self.white_fg = "#ffffff"
        self.black_fg = "#2C3E50"

        # --- Scaled Fonts ---
        self.font_large_title = ("Sarabun", int(55 * self.u_scale), "bold")
        self.font_medium_text = ("Sarabun", int(40 * self.u_scale), "bold")
        self.font_timer = ("Sarabun", int(70 * self.u_scale), "bold")
        self.font_pose_title = ("Sarabun", int(38 * self.u_scale), "bold")
        self.font_pose_action = ("Sarabun", int(28 * self.u_scale), "bold")
        self.font_btn_text = ("Sarabun", int(30 * self.u_scale), "bold")
        self.font_small = ("Sarabun", int(18 * self.u_scale), "bold")
        self.font_feedback = ("Sarabun", int(24 * self.u_scale), "bold") 

        # --- Layout Scaling ---
        top_bar_h = int(100 * self.scale_h)
        logo_size = int(80 * self.u_scale)
        self.camera_width = int(600 * self.scale_w) 
        self.camera_height = int(720 * self.scale_h)
        
        self.btn_h = int(65 * self.scale_h)
        self.btn_w = int(200 * self.scale_w)
        
        self.timer_canvas_size = int(240 * self.u_scale)
        self.timer_pad = 12

        history_data = self.get_history_from_file()
        if history_data:
            dates = sorted([h['date'].date() for h in history_data])
            today = datetime.now().date()
            if dates[-1] == today or dates[-1] == today - timedelta(days=1):
                self.streak_days = 1
                for i in range(len(dates)-1, 0, -1):
                    if (dates[i] - dates[i-1]).days == 1:
                        self.streak_days += 1
                    elif (dates[i] - dates[i-1]).days > 1:
                        break

        # --- Top Bar ---
        self.top_bar_frame = ctk.CTkFrame(self, fg_color=self.purple_bg, height=top_bar_h, corner_radius=0)
        self.top_bar_frame.pack(side="top", fill="x")
        self.top_bar_frame.pack_propagate(False)

        self.exit_button = ctk.CTkButton(
            self.top_bar_frame, text="×", font=("Arial", max(24, int(36 * self.u_scale)), "bold"),
            fg_color=self.red_btn, text_color=self.white_fg,
            hover_color=self.hover_red_bt, command=self.on_close,
            height=max(40, self.btn_h), width=max(40, self.btn_h), corner_radius=10
        )
        self.exit_button.pack(side="right", padx=int(20 * self.scale_w), pady=10)

        try:
            logo_image_pil = Image.open(resource_path("pictures", "logo.png"))
            self.logo_photo = ctk.CTkImage(light_image=logo_image_pil, size=(logo_size, logo_size))
            self.logo_label = ctk.CTkLabel(self.top_bar_frame, image=self.logo_photo, text="")
            self.logo_label.pack(side="left", padx=int(30 * self.scale_w), pady=int(10 * self.scale_h))
        except FileNotFoundError:
            self.logo_label = ctk.CTkLabel(self.top_bar_frame, text="LOGO", font=("Sarabun", 24, "bold"), text_color=self.white_fg)
            self.logo_label.pack(side="left", padx=30, pady=10)

        self.app_title_label = ctk.CTkLabel(
            self.top_bar_frame, text="AI-Powered Anti-trigger Fingers", font=self.font_large_title, text_color=self.white_fg
        )
        self.app_title_label.pack(side="left", padx=20, pady=10)

        # --- 1. Notification Banner (มุมขวาบน) ---
        self.notif_frame = ctk.CTkFrame(self.top_bar_frame, fg_color=self.green_btn, corner_radius=15)
        
        self.notif_label = ctk.CTkLabel(
            self.notif_frame, text="", font=("Sarabun", int(20 * self.u_scale), "bold"),
            text_color="#FFFFFF", wraplength=max(260, int(430 * self.scale_w)), justify="center"
        )
        self.notif_label.pack(side="left", padx=(15, 5), pady=8)

        try:
            star_img_pil = Image.open(resource_path("pictures", "star.png"))
            star_size = int(35 * self.u_scale)
            star_img_pil = star_img_pil.resize((star_size, star_size), Image.LANCZOS)
            self.star_photo = ImageTk.PhotoImage(star_img_pil)
            self.star_label = ctk.CTkLabel(self.notif_frame, image=self.star_photo, text="")
        except Exception:
            self.star_label = ctk.CTkLabel(self.notif_frame, text="⭐", font=("Sarabun", int(24 * self.u_scale)))
            
        self.star_label.pack(side="left", padx=(0, 15), pady=8)
        self.notif_hide_job = None
        # ------------------------------------

        streak_color = "#F1C40F" if self.streak_days > 0 else "#95A5A6"
        self.streak_label = ctk.CTkLabel(
            self.top_bar_frame, text=f"🔥 ต่อเนื่อง: {self.streak_days} วัน", 
            font=("Sarabun", int(30 * self.u_scale), "bold"), text_color=streak_color
        )
        self.streak_label.pack(side="right", padx=40, pady=10)

        # --- Main Content Grid ---
        self.main_content_frame = ctk.CTkFrame(self, fg_color=self.light_gray_bg_program)
        self.main_content_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)
        
        col_min = int(self.screen_width / 3) - 20
        self.main_content_frame.grid_columnconfigure(0, weight=1, minsize=col_min)
        self.main_content_frame.grid_columnconfigure(1, weight=1, minsize=col_min)
        self.main_content_frame.grid_columnconfigure(2, weight=1, minsize=col_min)
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(1, weight=1)
        self.main_content_frame.grid_rowconfigure(2, weight=1)

        # 1. Left Column: Camera
        self.camera_frame_bg = ctk.CTkFrame(self.main_content_frame, fg_color=self.light_gray_bg, corner_radius=20, border_width=1, border_color="#D5D8DC")
        self.camera_frame_bg.grid(row=0, column=0, rowspan=3, padx=10, pady=10, sticky="nsew") 
        
        placeholder = Image.new("RGB", (self.camera_width, self.camera_height), (220, 220, 220))
        self.camera_photo = ctk.CTkImage(light_image=placeholder, size=(self.camera_width, self.camera_height))
        self.camera_label = ctk.CTkLabel(self.camera_frame_bg, image=self.camera_photo, text="", corner_radius=20)
        self.camera_label.pack(expand=True, padx=10, pady=10)

        self.match_badge = ctk.CTkLabel(
            self.camera_label, text="Match: NO", font=("Sarabun", int(26 * self.u_scale), "bold"), 
            fg_color="#FFFFFF", text_color="#E74C3C", corner_radius=8, padx=15, pady=5
        )
        self.match_badge.place(x=15, y=15)
        
        self.env_badge = ctk.CTkLabel(
            self.camera_label, text="ระยะกล้อง/แสง: ตรวจสอบ...", font=("Sarabun", int(18 * self.u_scale), "bold"), 
            fg_color="#2C3E50", text_color="#FFFFFF", corner_radius=8, padx=10, pady=5
        )
        self.env_badge.place(x=15, y=65)

        # 2. Center Column: Set Info + Settings
        self.center_info_container = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.center_info_container.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10, pady=10)

        self.center_wrapper = ctk.CTkFrame(self.center_info_container, fg_color="transparent")
        self.center_wrapper.pack(expand=True, fill="both")

        self.set_times_frame = ctk.CTkFrame(self.center_wrapper, fg_color=self.light_gray_bg, corner_radius=20, border_width=1, border_color="#D5D8DC")
        self.set_times_frame.pack(side="top", fill="x", pady=(0, 10), ipady=5)

        self.times_line_frame = ctk.CTkFrame(self.set_times_frame, fg_color="transparent")
        self.times_line_frame.pack(side="top", pady=(10, 5))
        
        self.Label_times_text = ctk.CTkLabel(self.times_line_frame, text="รอบที่ : ", font=self.font_medium_text, text_color=self.black_fg)
        self.Label_times_text.pack(side="left", padx=(10, 0))
        self.Label_set_times_number = ctk.CTkLabel(self.times_line_frame, text=f"{self.round}", font=self.font_medium_text, text_color=self.blue_btn)
        self.Label_set_times_number.pack(side="left", padx=(0, 10))

        self.sets_line_frame = ctk.CTkFrame(self.set_times_frame, fg_color="transparent")
        self.sets_line_frame.pack(side="top", pady=(0, 5))
        
        self.Label_set_text = ctk.CTkLabel(self.sets_line_frame, text="เซ็ตที่ : ", font=self.font_medium_text, text_color=self.black_fg)
        self.Label_set_text.pack(side="left", padx=(10, 0))
        self.Label_set_number = ctk.CTkLabel(self.sets_line_frame, text=f"{self.set}", font=self.font_medium_text, text_color=self.green_btn)
        self.Label_set_number.pack(side="left", padx=(0, 10))

        self.round_progress = ctk.CTkProgressBar(self.set_times_frame, width=int(280 * self.scale_w), height=15, fg_color="#EAECEE", progress_color=self.green_btn, corner_radius=10)
        self.round_progress.pack(pady=(5, 5))
        self.round_progress.set(0) 
        
        self.reward_label = ctk.CTkLabel(self.set_times_frame, text="🌟 พร้อมแล้ว เริ่มลุยเลย!", font=("Sarabun", int(24 * self.u_scale), "bold"), text_color="#F39C12")
        self.reward_label.pack(side="top", pady=(0, 5))

        # --- 4. ข้อความ Guideline ตรงกลางจอ ---
        self.guideline_label = ctk.CTkLabel(
            self.center_wrapper, text="💡 ควรทำอย่างน้อย 2-3 เซ็ตต่อวัน", font=self.font_small, text_color="#7F8C8D", fg_color="transparent"
        )
        self.guideline_label.pack(side="top", pady=(0, 10))
        # ------------------------------------

        self.pose_text_frame = ctk.CTkFrame(self.center_wrapper, fg_color=self.light_gray_bg, corner_radius=20, border_width=1, border_color="#D5D8DC", height=int(160 * self.scale_h))
        self.pose_text_frame.pack(side="top", fill="x", pady=(5, 5))
        self.pose_text_frame.pack_propagate(False) 
        
        self.Label_pose_thai_text = ctk.CTkLabel(self.pose_text_frame, text=f"ท่าที่ {self.current_pose}", font=self.font_pose_title, text_color=self.black_fg)
        self.Label_pose_thai_text.pack(side="top", pady=(10, 0))
        
        self.Label_pose_action_text = ctk.CTkLabel(
            self.pose_text_frame, text=f"{self.pose_name[self.current_pose]}", font=self.font_pose_action, 
            text_color=self.purple_bg, wraplength=int(320 * self.scale_w)
        )
        self.Label_pose_action_text.pack(side="top", pady=(0, 5), padx=10)

        self.pose_feedback_label = ctk.CTkLabel(self.pose_text_frame, text="💬 รอตรวจจับท่าทาง...", font=self.font_feedback, text_color="#7F8C8D")
        self.pose_feedback_label.pack(side="top", pady=(0, 5))

        self.controls_btn_frame = ctk.CTkFrame(self.center_wrapper, fg_color="transparent")
        self.controls_btn_frame.pack(side="bottom", pady=(5, 0))
        
        self.start_stop_button = ctk.CTkButton(
            self.controls_btn_frame, text="▶ เริ่มต้น", font=self.font_btn_text, fg_color=self.green_btn,
            text_color=self.white_fg, command=lambda: self.toggle_start_pause(), height=self.btn_h, width=self.btn_w,
            hover_color=self.hover_green_bt, corner_radius=25
        )
        self.start_stop_button.pack(side="left", padx=10)
        
        self.reset_button = ctk.CTkButton(
            self.controls_btn_frame, text="🔄 รีเซ็ต", font=self.font_btn_text, fg_color=self.red_btn,
            text_color=self.white_fg, command=lambda: self.reset_action(), height=self.btn_h, width=self.btn_w,
            hover_color=self.hover_red_bt, corner_radius=25
        )
        self.reset_button.pack(side="left", padx=10)

        self.settings_panel = ctk.CTkScrollableFrame(self.center_wrapper, fg_color=self.light_gray_bg, corner_radius=20, border_width=1, border_color="#D5D8DC")
        self.settings_panel.pack(side="top", fill="both", expand=True, pady=(0, 5))
        
        hand_card = ctk.CTkFrame(self.settings_panel, fg_color="transparent")
        hand_card.pack(fill="x", padx=10, pady=(2, 0))
        ctk.CTkLabel(hand_card, text="🖐️ มือที่ฝึก:", font=self.font_small, text_color=self.black_fg).pack(anchor="w", padx=5, pady=0)
        
        self.target_hand_var = ctk.StringVar(value="ทั้งสอง")
        hand_btn_frame = ctk.CTkFrame(hand_card, fg_color="transparent")
        hand_btn_frame.pack(fill="x")
        
        btn_height = int(40 * self.scale_h)
        self.hand_btns = {}
        for h_val in ["ซ้าย", "ทั้งสอง", "ขวา"]:
            b = ctk.CTkButton(
                hand_btn_frame, text=h_val, font=self.font_small, height=btn_height,
                fg_color=self.purple_bg if h_val == "ทั้งสอง" else "#E5E7E9",
                text_color=self.white_fg if h_val == "ทั้งสอง" else self.black_fg,
                hover_color="#5B2C6F" if h_val == "ทั้งสอง" else "#BDC3C7",
                corner_radius=12, command=lambda val=h_val: self.select_hand(val)
            )
            b.pack(side="left", fill="x", expand=True, padx=4)
            self.hand_btns[h_val] = b

        diff_card = ctk.CTkFrame(self.settings_panel, fg_color="transparent")
        diff_card.pack(fill="x", padx=10, pady=(2, 0))
        ctk.CTkLabel(diff_card, text="⏱️ ระดับความยาก:", font=self.font_small, text_color=self.black_fg).pack(anchor="w", padx=5, pady=0)
        
        self.difficulty_var = ctk.StringVar(value="กลาง (5s)")
        diff_btn_frame = ctk.CTkFrame(diff_card, fg_color="transparent")
        diff_btn_frame.pack(fill="x")
        
        self.diff_btns = {}
        for d_val in ["ง่าย (3s)", "กลาง (5s)", "ยาก (7s)"]:
            b = ctk.CTkButton(
                diff_btn_frame, text=d_val, font=self.font_small, height=btn_height,
                fg_color=self.purple_bg if d_val == "กลาง (5s)" else "#E5E7E9",
                text_color=self.white_fg if d_val == "กลาง (5s)" else self.black_fg,
                hover_color="#5B2C6F" if d_val == "กลาง (5s)" else "#BDC3C7",
                corner_radius=12, command=lambda val=d_val: self.select_difficulty(val)
            )
            b.pack(side="left", fill="x", expand=True, padx=4)
            self.diff_btns[d_val] = b

        target_card = ctk.CTkFrame(self.settings_panel, fg_color="transparent")
        target_card.pack(fill="x", padx=10, pady=(2, 0))
        ctk.CTkLabel(target_card, text="🎯 เป้าหมายต่อวัน:", font=self.font_small, text_color=self.black_fg).pack(anchor="w", padx=5, pady=0)
        
        target_btn_frame = ctk.CTkFrame(target_card, fg_color="transparent")
        target_btn_frame.pack(fill="x")
        
        self.target_btns = {}
        for t_val in [3, 5]:
            b = ctk.CTkButton(
                target_btn_frame, text=f"{t_val} เซ็ต", font=self.font_small, height=btn_height,
                fg_color=self.purple_bg if t_val == 3 else "#E5E7E9",
                text_color=self.white_fg if t_val == 3 else self.black_fg,
                hover_color="#5B2C6F" if t_val == 3 else "#BDC3C7",
                corner_radius=12, command=lambda val=t_val: self.select_target(val)
            )
            b.pack(side="left", fill="x", expand=True, padx=4)
            self.target_btns[t_val] = b

        self.pain_frame = ctk.CTkFrame(self.settings_panel, fg_color="#FDF2E9", corner_radius=10)
        self.pain_frame.pack(fill="x", padx=10, pady=(5, 5))
        
        ctk.CTkLabel(self.pain_frame, text="📈 ประเมินความปวดก่อนฝึก (0-10)", font=self.font_small, text_color="#D35400").pack(pady=(2, 0))
        
        slider_inner = ctk.CTkFrame(self.pain_frame, fg_color="transparent")
        slider_inner.pack(fill="x", padx=10, pady=(0, 5))
        
        self.pain_var = ctk.IntVar(value=5)
        self.pain_val_lbl = ctk.CTkLabel(slider_inner, text="5", font=("Sarabun", 20, "bold"), text_color="#C0392B", width=30)
        self.pain_val_lbl.pack(side="left", padx=(5, 10))
        
        self.pain_slider = ctk.CTkSlider(slider_inner, from_=0, to=10, number_of_steps=10, variable=self.pain_var, command=lambda v: self.pain_val_lbl.configure(text=int(v)), progress_color="#E74C3C", button_color="#C0392B")
        self.pain_slider.pack(side="left", fill="x", expand=True, padx=5)
        
        self.pain_btn = ctk.CTkButton(slider_inner, text="บันทึก", font=self.font_small, fg_color="#E74C3C", hover_color="#C0392B", width=70, height=int(30 * self.scale_h), command=self.save_pain_log)
        self.pain_btn.pack(side="right", padx=(10, 5))

        # 3. Right Column: Timer, Image & Report
        self.right_info_container = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.right_info_container.grid(row=0, column=2, rowspan=3, sticky="nsew", padx=10, pady=10)

        self.timer_frame = ctk.CTkFrame(self.right_info_container, fg_color="transparent")
        self.timer_frame.pack(side="top", fill="x", pady=(0, 5), ipady=10)
        
        self.timer_canvas = ctk.CTkCanvas(self.timer_frame, width=self.timer_canvas_size, height=self.timer_canvas_size, bg="#F4F7F6", highlightthickness=0)
        self.timer_canvas.pack(pady=5)
        
        left_p = self.timer_pad
        right_p = self.timer_canvas_size - self.timer_pad
        self.timer_canvas.create_oval(left_p, left_p, right_p, right_p, outline=self.green_btn, width=15, tags="progress")
        center = self.timer_canvas_size // 2
        
        display_time = int(math.ceil(self.time_current))
        self.timer_text = self.timer_canvas.create_text(center, center, text=str(display_time), font=self.font_timer, fill=self.black_fg)

        self.breathing_label = ctk.CTkLabel(self.timer_frame, text="เตรียมพร้อมหายใจ...", font=("Sarabun", int(24 * self.u_scale), "bold"), text_color="#BDC3C7")
        self.breathing_label.pack(pady=(0, 5))

        self.timer_anim_job = None
        self._timer_anim_from = 0.0
        self._timer_anim_to = 0.0
        self._timer_anim_start = 0.0
        self._timer_anim_duration = 0.0

        img_size = int(320 * self.u_scale) 
        self.small_hand_bg = ctk.CTkFrame(self.right_info_container, fg_color=self.light_gray_bg, corner_radius=20, border_width=1, border_color="#D5D8DC")
        self.small_hand_bg.pack(side="top", fill="x", pady=(5, 10))

        try:
            small_hand_image_pil = Image.open(resource_path("pictures", "EX_POSE", "pose1.png"))
            self.small_hand_photo = ctk.CTkImage(light_image=small_hand_image_pil, size=(img_size, img_size))
            self.small_hand_label = ctk.CTkLabel(self.small_hand_bg, image=self.small_hand_photo, text="", corner_radius=15)
            self.small_hand_label.pack(padx=15, pady=15)
        except FileNotFoundError:
            self.small_hand_label = ctk.CTkLabel(self.small_hand_bg, text="รูปตัวอย่าง", font=("Sarabun", 16), width=img_size, height=img_size)
            self.small_hand_label.pack(padx=15, pady=15)

        self.log_button = ctk.CTkButton(
            self.right_info_container, text="📊 สถิติ & รายงานผล", font=self.font_btn_text, fg_color=self.purple_bg,
            text_color=self.white_fg, command=lambda: self.show_history_page(), height=self.btn_h,
            hover_color="#5B2C6F", corner_radius=25
        )
        self.log_button.pack(side="bottom", fill="x", pady=10) 

        # ==========================================
        # History Page
        # ==========================================
        self.history_page = ctk.CTkFrame(self, fg_color="#F4F7F6")
        
        self.history_header_frame = ctk.CTkFrame(self.history_page, fg_color=self.purple_bg, height=top_bar_h, corner_radius=0)
        self.history_header_frame.pack(side="top", fill="x")
        self.history_header_frame.pack_propagate(False)

        self.history_title = ctk.CTkLabel(self.history_header_frame, text="📊 สรุปผลการฝึกซ้อมของคุณ", font=self.font_large_title, text_color=self.white_fg)
        self.history_title.pack(pady=int(15 * self.scale_h))
        
        self.history_body_frame = ctk.CTkFrame(self.history_page, fg_color="transparent")
        self.history_body_frame.pack(fill="both", expand=True, padx=int(40 * self.scale_w), pady=15)
        
        self.kpi_frame = ctk.CTkFrame(self.history_body_frame, fg_color="transparent")
        self.kpi_frame.pack(side="top", fill="x", pady=(0, 10))

        self.history_content_frame = ctk.CTkFrame(self.history_body_frame, fg_color="transparent")
        self.history_content_frame.pack(side="bottom", fill="x", pady=(10, 10))

        self.history_log_wrapper = ctk.CTkFrame(self.history_content_frame, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#D5D8DC")
        self.history_log_wrapper.pack(side="left", fill="both", expand=True, padx=(0, 20))

        self.log_title = ctk.CTkLabel(self.history_log_wrapper, text="📝 บันทึกประวัติย้อนหลัง", font=("Sarabun", int(25 * self.u_scale), "bold"), text_color=self.black_fg)
        self.log_title.pack(anchor="w", padx=20, pady=(10, 0))

        self.history_textbox = ctk.CTkTextbox(
            self.history_log_wrapper, height=int(120 * self.scale_h), font=("Sarabun", int(20 * self.u_scale)),
            text_color=self.black_fg, fg_color="#F8F9F9", corner_radius=10, border_width=1, border_color="#E5E7E9"
        )
        self.history_textbox.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        self.back_button = ctk.CTkButton(
            self.history_content_frame, text="⬅️ กลับสู่หน้าหลัก", font=self.font_btn_text, fg_color=self.yellow_btn,
            text_color=self.black_fg, hover_color=self.hover_yellow_bt, command=self.show_main_page,
            height=int(80 * self.scale_h), width=int(260 * self.scale_w), corner_radius=20
        )
        self.back_button.pack(side="right", padx=10, pady=20) 

        self.chart_container_wrapper = ctk.CTkFrame(self.history_body_frame, fg_color="#FFFFFF", corner_radius=20, border_width=1, border_color="#D5D8DC")
        self.chart_container_wrapper.pack(side="top", fill="both", expand=True, pady=(0, 10), ipady=5, ipadx=5)

        self.chart_container = tk.Frame(self.chart_container_wrapper, bg="#FFFFFF")
        self.chart_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.pose_sounds = {1: ["001.mp3"], 2: ["002.mp3"], 3: ["003.mp3"], 4: ["004.mp3"], 5: ["005.mp3"]}
        self.current_chart = None

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"[Sound] Pygame mixer init error: {e}")

        self.running = False
        self.countdown_active = False
        self.countdown_job = None
        self.countdown_total = 0
        self.countdown_end_time = 0

        self.mp_running = True
        self.mp_thread = threading.Thread(target=self._mediapipe_loop, daemon=True)
        self.mp_thread.start()
        
        self.set_popup = ctk.CTkFrame(self, fg_color="#D5F5E3", corner_radius=20, border_width=3, border_color="#27AE60")
        
        self.set_popup_label = ctk.CTkLabel(
            self.set_popup, 
            text="ขอแสดงความยินดีคุณทำครบ 1 เซตแล้ว\nต่อเซตที่ 2 เลย! 🎉", 
            font=("Sarabun", int(35 * self.u_scale), "bold"), 
            text_color="#1E8449", justify="center"
        )
        self.set_popup_label.pack(padx=60, pady=40)

        self.goal_popup = ctk.CTkFrame(self, fg_color="#FCF3CF", corner_radius=20, border_width=3, border_color="#F1C40F")
        
        self.goal_popup_label = ctk.CTkLabel(
            self.goal_popup, 
            text="สุดยอดมาก! 🎉\nคุณทำครบเป้าหมายที่ตั้งไว้แล้ว!", 
            font=("Sarabun", int(40 * self.u_scale), "bold"), 
            text_color="#B7950B", justify="center"
        )
        self.goal_popup_label.pack(padx=60, pady=40)

        self.update_idletasks() 
        self.attributes("-fullscreen", True)
        self.update()

        self.check_sensor_loop()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def select_target(self, val):
        self.target_sets_var.set(val)
        for t_val, btn in self.target_btns.items():
            if t_val == val:
                btn.configure(fg_color=self.purple_bg, text_color=self.white_fg, hover_color="#5B2C6F")
            else:
                btn.configure(fg_color="#E5E7E9", text_color=self.black_fg, hover_color="#BDC3C7")
        if self.current_chart is not None:
            self.draw_progress_chart()
            
    def change_chart_timeframe(self, val):
        self.chart_timeframe = val
        if hasattr(self, "ax_cached") and self.ax_cached:
            self.ax_cached.clear()
        self.draw_progress_chart()

    def trigger_set_popup(self, current_set):
        next_set = current_set + 1
        msg = f"ขอแสดงความยินดีคุณทำครบ {current_set} เซตแล้ว\nต่อเซตที่ {next_set} เลย! 🎉"
        self.set_popup_label.configure(text=msg)
        
        self.set_popup.place(relx=0.5, rely=0.5, anchor="center")
        self.set_popup.tkraise()
        
        self.after(3000, self.set_popup.place_forget)

    def trigger_goal_popup(self, target):
        msg = f"สุดยอดมาก! 🎉\nคุณทำครบเป้าหมาย {target} เซ็ตแล้ว!"
        self.goal_popup_label.configure(text=msg)
        
        self.goal_popup.place(relx=0.5, rely=0.5, anchor="center")
        self.goal_popup.tkraise()
        
        self.after(3500, self.goal_popup.place_forget)

    def select_hand(self, val):
        self.target_hand_var.set(val)
        for h_val, btn in self.hand_btns.items():
            if h_val == val:
                btn.configure(fg_color=self.purple_bg, text_color=self.white_fg, hover_color="#5B2C6F")
            else:
                btn.configure(fg_color="#E5E7E9", text_color=self.black_fg, hover_color="#BDC3C7")

    def select_difficulty(self, val):
        self.difficulty_var.set(val)
        for d_val, btn in self.diff_btns.items():
            if d_val == val:
                btn.configure(fg_color=self.purple_bg, text_color=self.white_fg, hover_color="#5B2C6F")
            else:
                btn.configure(fg_color="#E5E7E9", text_color=self.black_fg, hover_color="#BDC3C7")
        self.change_difficulty(val)

    def change_difficulty(self, choice):
        if "3s" in choice: self.time_max = 3
        elif "7s" in choice: self.time_max = 7
        else: self.time_max = 5
        
        if not self.running:
            self.timer_reset()

    def save_pain_log(self):
        val = self.pain_var.get()
        self.write_log(f"PainLevel: {val}")
        self.pain_btn.configure(text="บันทึกแล้ว! ✅", fg_color=self.green_btn)
        self.after(2000, lambda: self.pain_btn.configure(text="บันทึก", fg_color="#E74C3C"))
        
    def get_history_from_file(self):
        current_time = time.time()
        if self._cached_history_data is not None and (current_time - self._last_history_read_time) < 2.0:
            return self._cached_history_data

        FILE_PATH = "Anti-Finger.txt"
        DAILY_TARGET_REPS = self.target_sets_var.get() * 3
        
        poses_per_rep = 5
        reps_per_set = 3 
        daily_poses = defaultdict(int)
        daily_pain = defaultdict(list)

        if not os.path.exists(FILE_PATH):
            return []

        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or not line.startswith("["):
                        continue
                    try:
                        date_str = line.split("]")[0][1:]
                        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        
                        if "PainLevel:" in line:
                            pain = int(line.split("PainLevel:")[1].strip())
                            daily_pain[date.date()].append(pain)
                        elif "ความปวดก่อน" in line:
                            try:
                                pain_str = line.split("ความปวดก่อน")[1].split("/")[0].strip()
                                if pain_str.isdigit():
                                    daily_pain[date.date()].append(int(pain_str))
                            except Exception:
                                pass

                        if "สำเร็จ" in line:
                            if "ฝึกครบทั้งหมด" in line:
                                try:
                                    num_poses = int(line.split("ฝึกครบทั้งหมด")[1].split("ท่า")[0].strip())
                                    daily_poses[date.date()] += num_poses
                                except Exception:
                                    daily_poses[date.date()] += 1
                            else:
                                daily_poses[date.date()] += 1

                    except Exception:
                        continue
        except Exception as e:
            print(f"Error reading file: {e}")
            return []

        if not daily_poses and not daily_pain:
            return []

        history = []
        all_dates = set(daily_poses.keys()).union(set(daily_pain.keys()))
        if not all_dates:
            return []
            
        first_day = min(all_dates)
        last_day = max(all_dates)
        day = first_day

        while day <= last_day:
            poses = daily_poses.get(day, 0)
            reps = poses / float(poses_per_rep) if poses_per_rep > 0 else 0
            sets_done = int(reps // reps_per_set)
            progress = min((reps / float(DAILY_TARGET_REPS)) * 100.0, 100.0) if DAILY_TARGET_REPS > 0 else 0.0
            
            avg_pain = None
            if daily_pain.get(day):
                avg_pain = sum(daily_pain[day]) / len(daily_pain[day])

            history.append({
                'date': datetime.combine(day, datetime.min.time()),
                'poses': poses,
                'reps': int(reps),
                'sets_done': sets_done,
                'progress': progress,
                'pain': avg_pain
            })
            day += timedelta(days=1)

        history.sort(key=lambda x: x['date'])
        
        self._cached_history_data = history
        self._last_history_read_time = current_time
        return history
        
    def update_kpi_dashboard(self, history):
        for widget in self.kpi_frame.winfo_children():
            widget.destroy()

        total_days = len(history)
        goal_met_days = sum(1 for h in history if h['progress'] >= 100)
        goal_met_pct = (goal_met_days / total_days * 100) if total_days > 0 else 0

        total_sets = sum(h['sets_done'] for h in history)

        pains = [h['pain'] for h in history if h['pain'] is not None]
        avg_pain = sum(pains) / len(pains) if pains else 0

        title_font = ("Sarabun", int(18 * self.u_scale), "bold")
        val_font = ("Sarabun", int(26 * self.u_scale), "bold")

        kpis = [
            ("🔥 ต่อเนื่อง (Streak)", f"{self.streak_days} วัน", "#E67E22"),
            ("🎯 วันที่ทำครบเป้า", f"{goal_met_pct:.0f}%", "#27AE60"),
            ("📚 เซ็ตสะสมรวม", f"{total_sets} เซ็ต", "#2980B9"),
            ("📉 ความปวดเฉลี่ย", f"{avg_pain:.1f}/10", "#8E44AD")
        ]

        for title, val, color in kpis:
            card = ctk.CTkFrame(self.kpi_frame, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#D5D8DC")
            card.pack(side="left", fill="both", expand=True, padx=5)

            ctk.CTkLabel(card, text=title, font=title_font, text_color="#7F8C8D").pack(pady=(10, 0))
            ctk.CTkLabel(card, text=val, font=val_font, text_color=color).pack(pady=(0, 10))

    def draw_progress_chart(self):
        for widget in self.chart_container.winfo_children():
            widget.destroy()
            
        history = self.get_history_from_file()

        if not history:
            label = tk.Label(self.chart_container, text="ไม่มีข้อมูลการฝึกซ้อม ลองไปฝึกสักเซ็ตสิครับ! 💪", bg=self.light_gray_bg, font=("Sarabun", 18, "bold"), fg="#7F8C8D")
            label.pack(fill="both", expand=True)
            return

        try:
            font_path = resource_path("Sarabun-Regular.ttf")
            if os.path.exists(font_path):
                thai_font_prop = fm.FontProperties(fname=font_path, size=13)
                title_font_prop = fm.FontProperties(fname=font_path, size=18, weight='bold')
            else:
                thai_font_prop = fm.FontProperties(family='Tahoma', size=13)
                title_font_prop = fm.FontProperties(family='Tahoma', size=18, weight='bold')

            main_frame = ctk.CTkFrame(self.chart_container, fg_color="transparent")
            main_frame.pack(fill="both", expand=True)

            control_frame = ctk.CTkFrame(main_frame, fg_color="#F8F9F9", width=int(280 * self.scale_w), corner_radius=15, border_width=1, border_color="#D5D8DC")
            control_frame.pack(side="right", fill="y", padx=(10, 0))
            control_frame.pack_propagate(False) 

            chart_frame = tk.Frame(main_frame, bg="white")
            chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

            tf_frame = ctk.CTkFrame(chart_frame, fg_color="#F8F9F9", corner_radius=10, height=40)
            tf_frame.pack(side="top", fill="x", pady=(0, 5))

            ctk.CTkLabel(tf_frame, text="⏳ ระยะเวลากราฟ:", font=("Sarabun", 16, "bold"), text_color=self.black_fg).pack(side="left", padx=15)

            for tf_val, tf_text in [(7, "7"), (14, "14"), (30, "30"), (90, "90"), (0, "All")]:
                btn_fg = self.purple_bg if self.chart_timeframe == tf_val else "#BDC3C7"
                btn = ctk.CTkButton(
                    tf_frame, text=tf_text, font=("Sarabun", 14, "bold"), height=30, width=60,
                    fg_color=btn_fg, text_color="white", corner_radius=8,
                    command=lambda v=tf_val: self.change_chart_timeframe(v)
                )
                btn.pack(side="left", padx=5, pady=5)

            ctk.CTkLabel(control_frame, text="📅 เลือกดูวันที่", font=("Sarabun", 20, "bold"), text_color=self.purple_bg).pack(anchor='w', pady=(20, 5), padx=20)
            
            date_var = tk.StringVar()
            style = ttk.Style()
            style.configure("TCombobox", padding=6, font=("Sarabun", 14))
            date_combo = ttk.Combobox(control_frame, textvariable=date_var, width=16, state='readonly', font=("Sarabun", 14))
            date_combo.pack(anchor='w', padx=20, pady=(0, 15))

            ctk.CTkLabel(control_frame, text="📌 คำอธิบายสัญลักษณ์", font=("Sarabun", 18, "bold"), text_color=self.black_fg).pack(anchor='w', pady=(10, 5), padx=20)
            ctk.CTkLabel(control_frame, text="🔴 สีแดง: ฝึกไม่ถึง 50%", font=("Sarabun", 16, "bold"), text_color="#E74C3C").pack(anchor='w', padx=20)
            ctk.CTkLabel(control_frame, text="🟢 สีเขียว: ฝึกผ่าน 50%", font=("Sarabun", 16, "bold"), text_color="#2ECC71").pack(anchor='w', padx=20)
            ctk.CTkLabel(control_frame, text="🟣 กราฟเส้น: ระดับความปวด", font=("Sarabun", 16, "bold"), text_color="#9B59B6").pack(anchor='w', padx=20)

            fb_container = ctk.CTkFrame(control_frame, fg_color="#FEF9E7", corner_radius=10, border_width=1, border_color="#F1C40F")
            fb_container.pack(fill="x", padx=15, pady=10, ipady=15)
            
            feedback_label = ctk.CTkLabel(fb_container, text="คลิกที่จุดบนกราฟ\nเพื่อดูรายละเอียด", font=("Sarabun", 15, "bold"), text_color="#5D6D7E", justify="left")
            feedback_label.pack(padx=10, pady=5)

            history_dict = {h['date'].date(): h for h in history}
            today = datetime.now().date()
            
            display_history = []
            if self.chart_timeframe > 0:
                start_date = today - timedelta(days=self.chart_timeframe - 1)
                for i in range(self.chart_timeframe):
                    d = start_date + timedelta(days=i)
                    if d in history_dict:
                        display_history.append(history_dict[d])
                    else:
                        display_history.append({
                            'date': datetime.combine(d, datetime.min.time()),
                            'poses': 0, 'reps': 0, 'sets_done': 0, 'progress': 0.0, 'pain': None
                        })
            else:
                start_date = min(history[0]['date'].date(), today) if history else today
                days_diff = (today - start_date).days + 1
                for i in range(max(1, days_diff)):
                    d = start_date + timedelta(days=i)
                    if d in history_dict:
                        display_history.append(history_dict[d])
                    else:
                        display_history.append({
                            'date': datetime.combine(d, datetime.min.time()),
                            'poses': 0, 'reps': 0, 'sets_done': 0, 'progress': 0.0, 'pain': None
                        })

            fig, ax = plt.subplots(figsize=(7, 3.5), dpi=90) 
            fig.patch.set_facecolor('#FFFFFF')
            ax.set_facecolor('#FFFFFF')
            self.ax_cached = ax 

            dates = [h['date'] for h in display_history]
            progresses = [h['progress'] for h in display_history]
            pains = [h['pain'] for h in display_history]

            colors = ['#2ECC71' if p >= 50 else '#E74C3C' for p in progresses]
            
            bars = ax.bar(dates, progresses, width=0.6, color=colors, alpha=0.9, edgecolor='black', linewidth=0.5)

            for bar, p in zip(bars, progresses):
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f'{int(p)}%', 
                        ha='center', va='bottom', fontproperties=thai_font_prop, color='#34495E',
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=2))

            ax.set_xticks(dates)
            ax.set_xticklabels([d.strftime('%d %b') for d in dates])
            
            if len(dates) > 15:
                step = math.ceil(len(dates) / 15)
                for i, label in enumerate(ax.xaxis.get_ticklabels()):
                    if i % step != 0 and i != len(dates) - 1:
                        label.set_visible(False)
            
            if len(dates) == 1:
                ax.set_xlim(dates[0] - timedelta(days=1), dates[0] + timedelta(days=1))
            elif len(dates) > 1:
                ax.set_xlim(dates[0] - timedelta(days=0.8), dates[-1] + timedelta(days=0.8))

            if any(p is not None for p in pains):
                ax2 = ax.twinx()
                p_dates = [d for d, p in zip(dates, pains) if p is not None]
                p_vals = [p for p in pains if p is not None]
                ax2.plot(p_dates, p_vals, color='#9B59B6', marker='s', linestyle='-.', linewidth=2.5, markersize=8)
                ax2.set_ylabel("ระดับความปวด (0-10)", fontproperties=thai_font_prop, color='#9B59B6', labelpad=15)
                ax2.set_ylim(-1, 15) 
                ax2.spines['right'].set_color('#9B59B6')
                ax2.tick_params(axis='y', colors='#9B59B6')

            ax.set_ylabel("ความสำเร็จในการฝึก (%)", fontproperties=thai_font_prop, color='#7F8C8D', labelpad=10)
            
            title_text = f"📈 สถิติความก้าวหน้าทางการรักษา ({self.chart_timeframe} วันล่าสุด)" if self.chart_timeframe > 0 else "📈 สถิติความก้าวหน้าทางการรักษา (ทั้งหมด)"
            ax.set_title(title_text, fontproperties=title_font_prop, pad=15, color='#2C3E50')

            ax.set_ylim(0, max(130, max(progresses)+30 if progresses else 130))
            ax.grid(True, axis='y', linestyle='--', alpha=0.3)
            ax.spines['top'].set_visible(False)
            ax.spines['left'].set_color('#BDC3C7')
            ax.spines['bottom'].set_color('#BDC3C7')
            fig.autofmt_xdate()
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

            date_list = [h['date'].strftime('%d-%b-%Y') for h in history]
            date_combo['values'] = date_list
            if date_list:
                date_combo.set(date_list[-1])

            points = []
            for i, p in enumerate(progresses):
                points.append((dates[i], p, display_history[i]['sets_done'], pains[i], i))

            def feedback_text(prog, prev_prog):
                if prog == 0: return "วันนี้ยังไม่ได้เริ่มเลย 🔴"
                elif prev_prog is not None and prog < prev_prog: return "ทำได้น้อยลงนิดหน่อย 📉"
                elif prev_prog is not None and prog > prev_prog: return "เก่งมาก! พัฒนาขึ้นแล้ว 📈"
                elif prog < 50: return "พยายามอีกนิดนึงนะ 💪"
                else: return "ยอดเยี่ยม! รักษามาตรฐานไว้ 🌟"

            def update_feedback(event=None):
                selected_date_str = date_var.get()
                if not selected_date_str: return
                try:
                    selected_date = datetime.strptime(selected_date_str, '%d-%b-%Y').date()
                    idx = next((i for i, h in enumerate(display_history) if h['date'].date() == selected_date), None)
                    if idx is not None:
                        prog = display_history[idx]['progress']
                        sets = display_history[idx]['sets_done']
                        pain = display_history[idx]['pain']
                        pain_txt = f"{pain:.1f}/10" if pain is not None else "ไม่ได้ระบุ"
                        prev_prog = display_history[idx-1]['progress'] if idx > 0 else None
                        fb = feedback_text(prog, prev_prog)
                        feedback_label.configure(text=f"📌 {selected_date_str}\nความสำเร็จ: {prog:.0f}% | เซ็ต: {sets}\nความปวด: {pain_txt}\n💬 {fb}")
                except Exception as e: print(f"Error: {e}")

            def on_click(event):
                if event.inaxes is None: return
                
                closest_idx = None
                min_dist = float('inf')
                for i, (date, prog, sets, pain, idx) in enumerate(points):
                    xdata = mdates.date2num(date)
                    dist = abs(event.xdata - xdata)
                    if dist < min_dist:
                        min_dist = dist
                        closest_idx = i
                
                if min_dist <= 0.6 and closest_idx is not None:
                    date, prog, sets, pain, idx = points[closest_idx]
                    prev_prog = progresses[idx-1] if idx > 0 else None
                    fb = feedback_text(prog, prev_prog)
                    pain_txt = f"{pain:.1f}/10" if pain is not None else "ไม่ได้ระบุ"
                    feedback_label.configure(text=f"📌 {date.strftime('%d-%b-%Y')}\nความสำเร็จ: {prog:.0f}% | เซ็ต: {sets}\nความปวด: {pain_txt}\n💬 {fb}")
                    date_var.set(date.strftime('%d-%b-%Y'))

            date_combo.bind("<<ComboboxSelected>>", update_feedback)
            canvas.mpl_connect("button_press_event", on_click)
            update_feedback()
            self.current_chart = (fig, canvas)

        except Exception as e:
            print(f"Error drawing chart: {e}")
            label = tk.Label(self.chart_container, text=f"Error: {e}", bg="white", font=("Sarabun", 12), fg="red")
            label.pack(fill="both", expand=True)

    def play_sounds_sequential(self, filename):
        def _play(f=filename):
            try:
                if not f.endswith(".mp3"):
                    f += ".mp3"
                sound_path = resource_path("Voices", f)
                if not os.path.isfile(sound_path):
                    print(f"[Sound] File not found: {sound_path}")
                    return
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                sound = pygame.mixer.Sound(sound_path)
                channel = sound.play()
                if channel is None:
                    print(f"[Sound] No available playback channel: {sound_path}")
                    return
                while channel.get_busy():
                    pygame.time.wait(100)
            except Exception as e:
                print(f"Sound error: {e}")
        threading.Thread(target=_play, daemon=True).start()

    def load_history(self):
        try:
            with open("Anti-Finger.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = ["ยังไม่มีประวัติการฝึกซ้อมเลย เริ่มต้นฝึกกันเถอะ!\n"]
        
        max_lines = 5000 
        if len(lines) > max_lines:
            lines = lines[-max_lines:]

        self.history_textbox.configure(state="normal")
        self.history_textbox.delete("1.0", "end")
        self.history_textbox.insert("end", "".join(lines))
        self.history_textbox.see("end")
        self.history_textbox.configure(state="disabled")

    def show_main_page(self):
        self.history_page.pack_forget()
        self.main_content_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)
        self.play_sounds_sequential("010.mp3")

    def show_history_page(self):
        self.main_content_frame.pack_forget()
        self.play_sounds_sequential("009.mp3")
        self.history_page.pack(side="top", fill="both", expand=True)
        self.update_kpi_dashboard(self.get_history_from_file())
        self.draw_progress_chart()
        self.load_history()

    def write_log(self, message):
        now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{now} เซ็ตที่ {self.set} รอบที่ {self.round} : {message}"
        try:
            with open("Anti-Finger.txt", "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
            print(log_message)
        except Exception as e:
            print(f"Error writing log: {e}")

    def _update_camera_label(self, pil_image, match, env_txt, env_col):
        try:
            self.camera_photo = ctk.CTkImage(light_image=pil_image, size=(self.camera_width, self.camera_height))
            self.camera_label.configure(image=self.camera_photo)
            
            if match:
                self.match_badge.configure(text="Match: YES", text_color="#2ECC71")
            else:
                self.match_badge.configure(text="Match: NO", text_color="#E74C3C")
                
            self.env_badge.configure(text=env_txt, text_color=env_col)
                
        except Exception as e:
            import traceback
            print(f"[UI ERROR] {e}")
            traceback.print_exc()

    def _mediapipe_loop(self):
        drawing_spec_landmark = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4)
        drawing_spec_connection = mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)

        hands = mp_hands.Hands(
            static_image_mode=False, max_num_hands=2,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )

        try:
            while self.mp_running:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = gray_frame.mean()
                
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                pose_match = False
                
                env_text = "สภาพแวดล้อม: ปกติ"
                env_color = "#2ECC71"

                if brightness < 60:
                    env_text = "แสงสว่างน้อยเกินไป"
                    env_color = "#E74C3C"

                if results.multi_hand_landmarks:
                    target_hand = self.target_hand_var.get()
                    hands_found = []
                    
                    for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                        mp_label = results.multi_handedness[idx].classification[0].label if results.multi_handedness else "Left"
                        physical_hand = "มือซ้าย" if mp_label == "Left" else "มือขวา"
                        
                        if target_hand == "ซ้าย" and physical_hand != "มือซ้าย": continue
                        if target_hand == "ขวา" and physical_hand != "มือขวา": continue
                        
                        hands_found.append(hand_landmarks)

                        x_min = min([lm.x for lm in hand_landmarks.landmark])
                        x_max = max([lm.x for lm in hand_landmarks.landmark])
                        y_min = min([lm.y for lm in hand_landmarks.landmark])
                        y_max = max([lm.y for lm in hand_landmarks.landmark])
                        
                        hand_diag = math.hypot((x_max - x_min)*w, (y_max - y_min)*h)
                        hand_diag = max(hand_diag, 1.0)
                        frame_diag = math.hypot(w, h)
                        ratio = hand_diag / frame_diag
                        
                        if brightness >= 60: 
                            if ratio < 0.15:
                                env_text = "ขยับมือใกล้กล้องอีกนิด"
                                env_color = "#F39C12"
                            elif ratio > 0.7:
                                env_text = "ขยับมือถอยหลังหน่อย"
                                env_color = "#F39C12"

                        mp_drawing.draw_landmarks(
                            frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                            drawing_spec_landmark, drawing_spec_connection
                        )

                    all_hands_correct = True
                    hands_to_check = len(hands_found)
                    
                    if target_hand == "ทั้งสอง" and hands_to_check < 2:
                        all_hands_correct = False
                    elif hands_to_check == 0:
                        all_hands_correct = False
                    else:
                        for hand_landmarks in hands_found:
                            lm = hand_landmarks.landmark
                            
                            def to_3d_pt(idx):
                                return (lm[idx].x, lm[idx].y, lm[idx].z)

                            def _angle_3d(p1, p2, p3):
                                v1 = (p1[0]-p2[0], p1[1]-p2[1], p1[2]-p2[2])
                                v2 = (p3[0]-p2[0], p3[1]-p2[1], p3[2]-p2[2])
                                dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
                                mag1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
                                mag2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)
                                if mag1 == 0 or mag2 == 0: return 0.0
                                cos_val = max(-1.0, min(1.0, dot / (mag1 * mag2)))
                                return math.degrees(math.acos(cos_val))

                            wrist = to_3d_pt(0) 

                            thumb_a = _angle_3d(to_3d_pt(4), to_3d_pt(2), wrist)
                            index_a = _angle_3d(to_3d_pt(8), to_3d_pt(5), wrist)
                            middle_a = _angle_3d(to_3d_pt(12), to_3d_pt(9), wrist)
                            ring_a = _angle_3d(to_3d_pt(16), to_3d_pt(13), wrist)
                            pinky_a = _angle_3d(to_3d_pt(20), to_3d_pt(17), wrist)

                            pose_ranges_3d = {
                                1: [(0, 200), (120, 200), (120, 200), (120, 200), (120, 200)], 
                                2: [(0, 200), (15, 170), (15, 170), (15, 170), (15, 170)],     
                                3: [(0, 200), (0, 110), (0, 110), (0, 110), (0, 110)],         
                                4: [(0, 200), (0, 140), (0, 140), (0, 140), (0, 140)],         
                                5: [(0, 200), (30, 180), (30, 180), (30, 180), (30, 180)],     
                            }

                            reqs = pose_ranges_3d.get(self.current_pose, pose_ranges_3d[1])
                            angles = [thumb_a, index_a, middle_a, ring_a, pinky_a]
                            
                            match_count = 0
                            for i in range(1, 5): 
                                mn, mx = reqs[i]
                                if mn <= angles[i] <= mx:
                                    match_count += 1
                            
                            if match_count < 3:
                                all_hands_correct = False
                                break

                    pose_match = all_hands_correct

                display_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(display_rgb)

                def _crop_and_resize(img, target_w, target_h):
                    src_w, src_h = img.size
                    target_ratio = target_w / target_h
                    src_ratio = src_w / src_h
                    if src_ratio > target_ratio:
                        new_w = int(src_h * target_ratio)
                        left = (src_w - new_w) // 2
                        img = img.crop((left, 0, left + new_w, src_h))
                    else:
                        new_h = int(src_w / target_ratio)
                        top = (src_h - new_h) // 2
                        img = img.crop((0, top, src_w, top + new_h))
                    return img.resize((target_w, target_h), Image.LANCZOS)

                pil_img = _crop_and_resize(pil_img, self.camera_width, self.camera_height)

                try:
                    self.after(0, lambda im=pil_img, m=pose_match, et=env_text, ec=env_color: (
                        self._update_camera_label(im, m, et, ec),
                        self.set_hand_posit_state(m)
                    ))
                except RuntimeError:
                    break
                time.sleep(0.02)
        finally:
            hands.close()

    def set_hand_posit_state(self, match):
        self.is_pose_currently_matched = match

    def timer_reset(self):
        self.time_current = self.time_max
        self.update_timer_display()
        self.reset_pic()
        self.breathing_label.configure(text="เตรียมพร้อม...", text_color="#BDC3C7")
        try:
            self.update_EX_pose()
        except Exception:
            pass

    def reset_pic(self):
        self.timer_canvas.delete("progress")
        l = self.timer_pad
        r = self.timer_canvas_size - self.timer_pad
        self.timer_canvas.create_oval(l, l, r, r, outline=self.green_btn, width=15, tags="progress")

    def update_timer_display(self):
        try:
            progress = max(0.0, min(1.0, (self.time_max - self.time_current) / float(self.time_max)))
            extent = 360 * progress
            self.timer_canvas.delete("progress")
            l = self.timer_pad
            r = self.timer_canvas_size - self.timer_pad
            self.timer_canvas.create_arc(l, l, r, r, start=-90, extent=-extent, style="arc", width=15, outline=self.green_btn, tags="progress")
            
            display_time = int(math.ceil(self.time_current))
            self.timer_canvas.itemconfig(self.timer_text, text=str(display_time))
        except Exception:
            pass

    def reset_feedback(self):
        self.pose_feedback_label.configure(text="💬 ลุยท่าต่อไปได้เลย!", text_color="#F39C12")

    def update_text(self):
        self.Label_pose_action_text.configure(text=f"{self.pose_name[self.current_pose]}")
        self.Label_pose_thai_text.configure(text=f"ท่าที่ {self.current_pose}")

    def update_round(self):
        self.Label_set_times_number.configure(text=f"{self.round}")
        self.Label_set_number.configure(text=f"{self.set}")
        
        self.round_progress.set(self.round / 3.0)

        target = self.target_sets_var.get()
        if self.set == 0 and self.round == 0:
            reward_msg = "🌟 พร้อมแล้ว เริ่มลุยเลย!"
            color = "#F39C12"
        elif self.round == 0 and self.set > 0:
            reward_msg = f"🏆 สุดยอด! จบเซ็ตที่ {self.set} แล้ว เตรียมลุยเซ็ตต่อไป!"
            color = "#27AE60"
        else:
            reward_msg = f"🔥 ลุยต่อ! (เซ็ตที่ {self.set + 1}/{target} | รอบที่ {self.round}/3)"
            color = "#D35400"
            
        self.reward_label.configure(text=reward_msg, text_color=color)

    def update_EX_pose(self):
        try:
            img_size = int(320 * self.u_scale)
            small_hand_image_pil = Image.open(resource_path("pictures", "EX_POSE", f"pose{self.current_pose}.png"))
            self.small_hand_photo = ctk.CTkImage(light_image=small_hand_image_pil, size=(img_size, img_size))
            self.small_hand_label.configure(image=self.small_hand_photo)
        except:
            pass

    def toggle_start_pause(self):
        if self.start_stop_button.cget("text") == "▶ เริ่มต้น":
            self.start_stop_button.configure(text="⏸ หยุด", fg_color=self.yellow_btn, hover_color=self.hover_yellow_bt)
            self.play_sounds_sequential("006.mp3")
            self.start_pose_countdown(2)
        else:
            self.start_stop_button.configure(text="▶ เริ่มต้น", fg_color=self.green_btn, hover_color=self.hover_green_bt)
            self.running = False
            self._cancel_countdown()
            self.play_sounds_sequential("007.mp3")

    def start_pose_countdown(self, seconds: int):
        self._cancel_countdown()
        self.countdown_active = True
        self.countdown_total = max(1, seconds)
        self.countdown_end_time = time.time() + self.countdown_total
        self.countdown_job = self.after(0, self._animate_countdown)

    def _animate_countdown(self):
        if not self.countdown_active:
            return
        now = time.time()
        remaining = self.countdown_end_time - now
        if remaining <= 0:
            self.countdown_active = False
            self.countdown_job = None
            self.running = True
            self.is_pose_currently_matched = False
            try:
                display_time = int(math.ceil(self.time_current))
                self.timer_canvas.itemconfig(self.timer_text, text=str(display_time))
                self.timer_canvas.delete("progress")
                l = self.timer_pad
                r = self.timer_canvas_size - self.timer_pad
                self.timer_canvas.create_oval(l, l, r, r, outline=self.green_btn, width=15, tags="progress")
            except Exception:
                pass
                
            try:
                self.play_sounds_sequential(self.pose_sounds[self.current_pose][0])
            except Exception:
                pass

        frac = max(0.0, min(1.0, remaining / float(self.countdown_total)))
        extent = 360 * frac

        try:
            self.timer_canvas.delete("progress")
            l = self.timer_pad
            r = self.timer_canvas_size - self.timer_pad
            self.timer_canvas.create_arc(l, l, r, r, start=-90, extent=-extent, style="arc", width=15, outline="#FFA500", tags="progress")
            secs = int(math.ceil(remaining))
            self.timer_canvas.itemconfig(self.timer_text, text=str(secs))
        except Exception:
            pass

        try:
            self.countdown_job = self.after(50, self._animate_countdown)
        except Exception:
            self.countdown_active = False
            self.countdown_job = None

    def _cancel_countdown(self):
        if self.countdown_active:
            self.countdown_active = False
            if self.countdown_job:
                try:
                    self.after_cancel(self.countdown_job)
                except Exception:
                    pass
                self.countdown_job = None
            try:
                display_time = int(math.ceil(self.time_current))
                self.timer_canvas.itemconfig(self.timer_text, text=str(display_time))
                self.timer_canvas.delete("progress")
                l = self.timer_pad
                r = self.timer_canvas_size - self.timer_pad
                self.timer_canvas.create_oval(l, l, r, r, outline=self.green_btn, width=15, tags="progress")
            except Exception:
                pass

    def reset_action(self):
        self.running = False
        try:
            self._cancel_countdown()
        except Exception:
            pass

        self.start_stop_button.configure(text="▶ เริ่มต้น", fg_color=self.green_btn, hover_color=self.hover_green_bt)
        self.round = 0
        self.set = 0
        self.current_pose = 1
        self.timer_reset()
        self.update_text()
        self.update_round()
        self.reset_feedback()

        try:
            self.play_sounds_sequential("008.mp3")
        except Exception as e:
            print(f"[reset_action] play sound error: {e}")

    def on_close(self):
        self.mp_running = False
        self.running = False
        try:
            if hasattr(self, "mp_thread") and self.mp_thread.is_alive():
                self.mp_thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        self.destroy()
        os._exit(0)
        
    def check_sensor_loop(self):
        if self.running:
            matched = getattr(self, "is_pose_currently_matched", False)
            
            if matched:
                if self.time_current > 0:
                    self.time_current -= 0.1 
                    self.update_timer_display()
                    
                    elapsed = self.time_max - self.time_current
                    if self.time_max == 3:
                        msg, color = ("สูดหายใจเข้าลึกๆ...", self.blue_btn) if elapsed <= 1 else ("ค่อยๆ ผ่อนลมหายใจ...", self.green_btn)
                    elif self.time_max == 7:
                        if elapsed <= 2: msg, color = "สูดหายใจเข้าลึกๆ...", self.blue_btn
                        elif elapsed <= 4: msg, color = "กลั้นลมหายใจไว้...", self.yellow_btn
                        else: msg, color = "ค่อยๆ ผ่อนลมหายใจ...", self.green_btn
                    else: 
                        if elapsed <= 2: msg, color = "สูดหายใจเข้าลึกๆ...", self.blue_btn
                        elif elapsed <= 3: msg, color = "กลั้นลมหายใจไว้...", self.yellow_btn
                        else: msg, color = "ค่อยๆ ผ่อนลมหายใจ...", self.green_btn
                    
                    self.breathing_label.configure(text=msg, text_color=color)

                if self.time_current <= 0:
                    self._on_pose_success()
            else:
                self.breathing_label.configure(text="⏸ กรุณาค้างท่าให้ถูกต้อง...", text_color="#E74C3C")

        try:
            self.after(100, self.check_sensor_loop)
        except Exception:
            pass

    def _on_pose_success(self):
        try:
            completed_pose_name = self.pose_name[self.current_pose]
            self.write_log(f"ท่า {completed_pose_name} สำเร็จ! 🌟")
            
            # --- ส่งแจ้งเตือน Notification Banner สีเขียวมุมขวาบน ---
            self.show_success_notification(completed_pose_name)
            
            encouragements = ["เก่งมาก! 👏", "ยอดเยี่ยม! 🌟", "ท่าสวยเป๊ะ! ✨", "สุดยอด! 🔥", "เยี่ยมไปเลย! 🎯"]
            msg = random.choice(encouragements)
            self.pose_feedback_label.configure(text=f"🎉 สำเร็จ! {msg}", text_color="#27AE60")
            self.breathing_label.configure(text="ผ่อนคลาย...", text_color="#BDC3C7")
            
            try:
                from ctypes import windll
                windll.kernel32.Beep(1000, 300)
            except Exception:
                pass
                
        except Exception as e:
            print(f"[_on_pose_success] write_log error: {e}")

        self.current_pose += 1
        if self.current_pose > 5:
            self.current_pose = 1
            self.round += 1
            
            if self.round >= 3:
                self.round = 0
                self.set += 1
                
                target = self.target_sets_var.get()
                if self.set >= target:
                    self.trigger_goal_popup(target)
                    
                    try:
                        from ctypes import windll
                        windll.kernel32.Beep(1000, 150)
                        time.sleep(0.1)
                        windll.kernel32.Beep(1200, 200)
                        time.sleep(0.1)
                        windll.kernel32.Beep(1500, 300)
                    except Exception:
                        pass
                        
                    self.after(3500, self.reset_action)
                else:
                    self.trigger_set_popup(self.set)

        try:
            self.update_round()
            self.timer_reset()
            self.update_EX_pose()
            self.update_text()
            
            self.after(2500, self.reset_feedback)
            
            sound_file = self.pose_sounds.get(self.current_pose, [None])[0]
            if sound_file:
                try:
                    self.play_sounds_sequential(sound_file)
                except Exception:
                    pass
        except Exception:
            pass

    # --- ฟังก์ชันควบคุม Notification Banner ด้านขวาบน ---
    def show_success_notification(self, pose_name):
        message = f"คุณทำท่า{pose_name}สำเร็จแล้ว!"
        self.notif_label.configure(text=message)

        # ให้กล่องแจ้งเตือนใช้พื้นที่ด้านขวาได้เต็ม โดยซ่อนสถิติต่อเนื่องชั่วคราว
        self.streak_label.pack_forget()
        self.notif_frame.pack(side="right", padx=int(25 * self.scale_w), pady=10)

        if self.notif_hide_job:
            self.after_cancel(self.notif_hide_job)

        self.notif_hide_job = self.after(2500, self._hide_notification)

    def _hide_notification(self):
        self.notif_frame.pack_forget()
        self.streak_label.pack(side="right", padx=40, pady=10)
        self.notif_hide_job = None
    # -----------------------------------------------

if __name__ == "__main__":
    app = AntiTriggerFingersApp()
    app.mainloop()
