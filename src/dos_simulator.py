import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import time
import random
import os
import csv
import socket
import sys
from datetime import datetime
import platform
import webbrowser
from tkinter import font as tkfont
import json

# Check for optional dependencies
try:
    import psutil
    psutil_available = True
except ImportError:
    psutil_available = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    from matplotlib import style
    style.use('default')  # Changed to default for white theme
    matplotlib_available = True
except ImportError:
    matplotlib_available = False

# Constants
DEFAULT_TARGET = '192.168.56.1'
DEFAULT_PORT = 80
DEFAULT_FAKE_IP = '172.11.14.24'
MAX_HISTORY = 300

# Single White Theme (removed dark theme and toggle)
WHITE_THEME = {
    'bg': '#FFFFFF',
    'text': '#212121',
    'accent': '#2196F3',
    'secondary': '#F5F5F5',
    'highlight': '#FF9800',
    'success': '#4CAF50',
    'danger': '#F44336',
    'warning': '#FFC107',
    'graph_bg': '#FFFFFF',
    'entry_bg': '#FFFFFF',
    'border': '#E0E0E0'
}

# Global variables with proper initialization
connection_status = 0
lock = threading.Lock()
attack_running = False
threads = []
fake_requests_history = []
start_time = None
peak_requests = 0
total_bandwidth = 0

attack_types = {
    'SYN Flood': {'min_delay': 0.001, 'max_delay': 0.01, 'packet_size': 64},
    'UDP Flood': {'min_delay': 0.005, 'max_delay': 0.02, 'packet_size': 512},
    'HTTP Flood': {'min_delay': 0.01, 'max_delay': 0.05, 'packet_size': 1024},
    'Slowloris': {'min_delay': 0.1, 'max_delay': 0.5, 'packet_size': 128},
    'ICMP Flood': {'min_delay': 0.002, 'max_delay': 0.015, 'packet_size': 256},
    'DNS Amplification': {
        'min_delay': 0.02, 
        'max_delay': 0.1, 
        'packet_size': 4000,
        'requires_reflector': True
    },
    'NTP Amplification': {
        'min_delay': 0.01, 
        'max_delay': 0.05, 
        'packet_size': 468,
        'requires_reflector': True
    },
    'SNMP Amplification': {
        'min_delay': 0.03, 
        'max_delay': 0.1, 
        'packet_size': 1500,
        'requires_reflector': True
    }
}

class ModernTooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.showtip)
        self.widget.bind("<Leave>", self.hiddentip)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        frame = tk.Frame(tw, bg="#333", relief='solid', borderwidth=1)
        frame.pack()
        label = tk.Label(frame, text=self.text, justify='left',
                        bg="#333", fg="white", relief='solid', borderwidth=0,
                        font=('Helvetica', '10'))
        label.pack()

    def hiddentip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class DoSSimulatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced DoS Simulator (Educational Purposes Only)")
        self.geometry("1400x900")
        self.minsize(1200, 800)
        
        self.settings_file = "dos_simulator_settings.json"
        self.load_settings()
        self.init_vars()
        self.setup_ui()
        
        self.after(1000, self.update_graph)
        self.after(5000, self.update_system_stats)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.bind("<F1>", self.show_help)
        self.bind("<Control-s>", lambda e: self.start_simulation())
        self.bind("<Control-q>", lambda e: self.stop_simulation())

    def init_vars(self):
        self.target = tk.StringVar(value=self.settings.get('target', DEFAULT_TARGET))
        self.port = tk.IntVar(value=self.settings.get('port', DEFAULT_PORT))
        self.fake_ip = tk.StringVar(value=self.settings.get('fake_ip', DEFAULT_FAKE_IP))
        self.num_threads = tk.IntVar(value=self.settings.get('num_threads', 10))
        self.min_delay = tk.DoubleVar(value=self.settings.get('min_delay', 0.01))
        self.max_delay = tk.DoubleVar(value=self.settings.get('max_delay', 0.05))
        self.packet_size = tk.IntVar(value=self.settings.get('packet_size', 64))
        self.attack_type = tk.StringVar(value=self.settings.get('attack_type', 'SYN Flood'))
        self.reflector_ip = tk.StringVar(value=self.settings.get('reflector_ip', '8.8.8.8'))
        self.reflector_port = tk.IntVar(value=self.settings.get('reflector_port', 53))
        
        self.total_label_var = tk.StringVar(value="Total: 0")
        self.avg_label_var = tk.StringVar(value="Avg/sec: 0")
        self.peak_label_var = tk.StringVar(value="Peak/sec: 0")
        self.bandwidth_var = tk.StringVar(value="Bandwidth: 0 KB/s")
        self.status_graph_val = tk.StringVar(value="Ready")
        self.cpu_usage_var = tk.StringVar(value="CPU: N/A")
        self.mem_usage_var = tk.StringVar(value="RAM: N/A")
        self.log_level = tk.StringVar(value=self.settings.get('log_level', 'Normal'))

    def setup_ui(self):
        self.configure_theme()
        self.create_menu()
        self.create_main_frames()
        self.create_config_controls()
        self.create_stats_controls()
        self.create_system_controls()
        self.create_graph_frame()
        self.create_log_frame()
        
        self.graph_status = tk.Label(self.graph_frame, textvariable=self.status_graph_val, 
                                   bg=self.get_theme_color('bg'), fg=self.get_theme_color('accent'),
                                   font=('Helvetica', 10, 'bold'))
        self.graph_status.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 5))

    def configure_theme(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        bg = self.get_theme_color('bg')
        text = self.get_theme_color('text')
        secondary = self.get_theme_color('secondary')
        accent = self.get_theme_color('accent')
        
        self.configure(bg=bg)
        
        # Configure styles for white theme
        self.style.configure('.', background=bg, foreground=text)
        self.style.configure('TButton', background=secondary, foreground=text, 
                           borderwidth=1, relief='solid')
        self.style.map('TButton', 
                      background=[('active', accent)],
                      foreground=[('active', 'white')])
        
        self.style.configure('Accent.TButton', 
                           background=self.get_theme_color('success'),
                           foreground='white',
                           font=('Helvetica', 10, 'bold'))
        
        self.style.configure('Danger.TButton', 
                           background=self.get_theme_color('danger'),
                           foreground='white', 
                           font=('Helvetica', 10, 'bold'))
        
        self.style.configure('TEntry', 
                           fieldbackground=self.get_theme_color('entry_bg'),
                           foreground=text,
                           borderwidth=1)
        
        self.style.configure('TCombobox', 
                           fieldbackground=self.get_theme_color('entry_bg'),
                           foreground=text)
        
        self.style.configure('TLabelframe', 
                           background=bg, 
                           foreground=text,
                           bordercolor=self.get_theme_color('border'))
        
        self.style.configure('TLabelframe.Label', 
                           background=bg, 
                           foreground=accent,
                           font=('Helvetica', 10, 'bold'))
        
        self.style.configure('TLabel', 
                           background=bg, 
                           foreground=text)

    def get_theme_color(self, color_name):
        return WHITE_THEME.get(color_name, '#FFFFFF')

    def create_menu(self):
        menubar = tk.Menu(self, bg=self.get_theme_color('bg'), fg=self.get_theme_color('text'))
        
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.get_theme_color('bg'), fg=self.get_theme_color('text'))
        file_menu.add_command(label="New Simulation", command=self.reset_simulation)
        file_menu.add_command(label="Save Logs...", command=self.export_logs)
        file_menu.add_command(label="Export CSV...", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        edit_menu = tk.Menu(menubar, tearoff=0, bg=self.get_theme_color('bg'), fg=self.get_theme_color('text'))
        edit_menu.add_command(label="Clear Logs", command=self.clear_logs)
        edit_menu.add_separator()
        edit_menu.add_command(label="Settings", command=self.show_settings)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        view_menu = tk.Menu(menubar, tearoff=0, bg=self.get_theme_color('bg'), fg=self.get_theme_color('text'))
        # Removed theme toggle options
        view_menu.add_separator()
        view_menu.add_radiobutton(label="Verbose Logging", variable=self.log_level, value="Verbose")
        view_menu.add_radiobutton(label="Normal Logging", variable=self.log_level, value="Normal")
        view_menu.add_radiobutton(label="Minimal Logging", variable=self.log_level, value="Minimal")
        menubar.add_cascade(label="View", menu=view_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0, bg=self.get_theme_color('bg'), fg=self.get_theme_color('text'))
        help_menu.add_command(label="Help", command=self.show_help, accelerator="F1")
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menubar)

    def create_main_frames(self):
        self.main_container = tk.Frame(self, bg=self.get_theme_color('bg'))
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.left_panel = tk.Frame(self.main_container, bg=self.get_theme_color('bg'))
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        self.right_panel = tk.Frame(self.main_container, bg=self.get_theme_color('bg'))
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_config_controls(self):
        config_frame = ttk.LabelFrame(self.left_panel, text="Attack Configuration")
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Attack Type:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.attack_type_menu = ttk.Combobox(config_frame, textvariable=self.attack_type, 
                                           values=list(attack_types.keys()), state='readonly')
        self.attack_type_menu.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        self.attack_type_menu.bind("<<ComboboxSelected>>", lambda e: [self.update_attack_params(), self.toggle_reflector_visibility()])
        
        ttk.Label(config_frame, text="Target:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.target_entry = ttk.Entry(config_frame, textvariable=self.target)
        self.target_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(config_frame, text="Port:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.port_entry = ttk.Entry(config_frame, textvariable=self.port)
        self.port_entry.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(config_frame, text="Fake IP:").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        self.fake_ip_entry = ttk.Entry(config_frame, textvariable=self.fake_ip)
        self.fake_ip_entry.grid(row=3, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(config_frame, text="Threads:").grid(row=4, column=0, sticky='w', padx=5, pady=2)
        self.threads_slider = ttk.Scale(config_frame, from_=1, to=100, variable=self.num_threads)
        self.threads_slider.grid(row=4, column=1, sticky='ew', padx=5, pady=2)
        self.threads_value_label = ttk.Label(config_frame, textvariable=self.num_threads)
        self.threads_value_label.grid(row=4, column=2, padx=5, pady=2)
        
        ttk.Label(config_frame, text="Min Delay (s):").grid(row=5, column=0, sticky='w', padx=5, pady=2)
        self.min_delay_entry = ttk.Entry(config_frame, textvariable=self.min_delay)
        self.min_delay_entry.grid(row=5, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(config_frame, text="Max Delay (s):").grid(row=6, column=0, sticky='w', padx=5, pady=2)
        self.max_delay_entry = ttk.Entry(config_frame, textvariable=self.max_delay)
        self.max_delay_entry.grid(row=6, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(config_frame, text="Packet Size (bytes):").grid(row=7, column=0, sticky='w', padx=5, pady=2)
        self.packet_size_entry = ttk.Entry(config_frame, textvariable=self.packet_size)
        self.packet_size_entry.grid(row=7, column=1, sticky='ew', padx=5, pady=2)
        
        self.reflector_frame = ttk.LabelFrame(config_frame, text="Reflector Configuration")
        self.reflector_frame.grid(row=8, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        
        ttk.Label(self.reflector_frame, text="Reflector IP:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.reflector_ip_entry = ttk.Entry(self.reflector_frame, textvariable=self.reflector_ip)
        self.reflector_ip_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(self.reflector_frame, text="Reflector Port:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.reflector_port_entry = ttk.Entry(self.reflector_frame, textvariable=self.reflector_port)
        self.reflector_port_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=9, column=0, columnspan=3, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="Start Attack", command=self.start_simulation, 
                                  style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Attack", command=self.stop_simulation, 
                                 style='Danger.TButton')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_btn = ttk.Button(button_frame, text="Reset", command=self.reset_simulation)
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        
        config_frame.columnconfigure(1, weight=1)
        self.toggle_reflector_visibility()

    def toggle_reflector_visibility(self):
        attack = self.attack_type.get()
        if attack in attack_types and attack_types[attack].get('requires_reflector', False):
            self.reflector_frame.grid()
        else:
            self.reflector_frame.grid_remove()

    def create_stats_controls(self):
        stats_frame = ttk.LabelFrame(self.left_panel, text="Statistics")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(stats_grid, textvariable=self.total_label_var, 
                 font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        
        ttk.Label(stats_grid, textvariable=self.avg_label_var,
                 font=('Helvetica', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=5, pady=2)
        
        ttk.Label(stats_grid, textvariable=self.peak_label_var,
                 font=('Helvetica', 10, 'bold')).grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Label(stats_grid, textvariable=self.bandwidth_var,
                 font=('Helvetica', 10, 'bold')).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        stats_grid.columnconfigure(0, weight=1)
        stats_grid.columnconfigure(1, weight=1)

    def create_system_controls(self):
        sys_frame = ttk.LabelFrame(self.left_panel, text="System Monitor")
        sys_frame.pack(fill=tk.X, padx=5, pady=5)
        
        sys_grid = ttk.Frame(sys_frame)
        sys_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(sys_grid, textvariable=self.cpu_usage_var,
                 font=('Helvetica', 9)).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        
        ttk.Label(sys_grid, textvariable=self.mem_usage_var,
                 font=('Helvetica', 9)).grid(row=1, column=0, sticky='w', padx=5, pady=2)
        
        sys_info = f"OS: {platform.system()} {platform.release()} | Python: {platform.python_version()}"
        ttk.Label(sys_grid, text=sys_info,
                 font=('Helvetica', 8)).grid(row=2, column=0, sticky='w', padx=5, pady=2)

    def create_graph_frame(self):
        self.graph_frame = ttk.LabelFrame(self.right_panel, text="Attack Visualization")
        self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        if matplotlib_available:
            self.fig = Figure(figsize=(6, 4), dpi=100, facecolor=self.get_theme_color('graph_bg'))
            self.ax = self.fig.add_subplot(111)
            self.ax.set_facecolor(self.get_theme_color('secondary'))
            self.ax.set_title("Real-Time Attack Traffic", color=self.get_theme_color('text'))
            self.ax.set_xlabel("Time (seconds)", color=self.get_theme_color('text'))
            self.ax.set_ylabel("Requests per second", color=self.get_theme_color('text'))
            self.ax.tick_params(axis='x', colors=self.get_theme_color('text'))
            self.ax.tick_params(axis='y', colors=self.get_theme_color('text'))
            
            self.line, = self.ax.plot([], [], color=self.get_theme_color('accent'), linewidth=2)
            self.ax.grid(True, color=self.get_theme_color('border'), alpha=0.3)
            
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            toolbar = NavigationToolbar2Tk(self.canvas, self.graph_frame, pack_toolbar=False)
            toolbar.update()
            toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        else:
            ttk.Label(self.graph_frame, text="Matplotlib not available - graphs disabled").pack(expand=True)

    def create_log_frame(self):
        log_frame = ttk.LabelFrame(self.right_panel, text="Attack Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        self.log_output = scrolledtext.ScrolledText(
            log_frame, 
            font=("Consolas", 10), 
            state='disabled', 
            wrap='word', 
            bg=self.get_theme_color('secondary'), 
            fg=self.get_theme_color('text'),
            insertbackground=self.get_theme_color('text'),
            selectbackground=self.get_theme_color('accent'),
            padx=5,
            pady=5
        )
        self.log_output.pack(fill=tk.BOTH, expand=True)
        
        self.log_output.tag_config('info', foreground='blue')
        self.log_output.tag_config('warning', foreground='orange')
        self.log_output.tag_config('error', foreground='red')
        self.log_output.tag_config('debug', foreground='gray')
        self.log_output.tag_config('success', foreground='green')
        self.log_output.tag_config('danger', foreground='red')

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
            else:
                self.settings = {}
            if 'reflector_ip' not in self.settings:
                self.settings['reflector_ip'] = '8.8.8.8'
            if 'reflector_port' not in self.settings:
                self.settings['reflector_port'] = 53
        except Exception as e:
            self.settings = {}
            self.log(f"[!] Error loading settings: {e}", 'error')

    def save_settings(self):
        self.settings = {
            'target': self.target.get(),
            'port': self.port.get(),
            'fake_ip': self.fake_ip.get(),
            'num_threads': self.num_threads.get(),
            'min_delay': self.min_delay.get(),
            'max_delay': self.max_delay.get(),
            'packet_size': self.packet_size.get(),
            'attack_type': self.attack_type.get(),
            'log_level': self.log_level.get(),
            'reflector_ip': self.reflector_ip.get(),
            'reflector_port': self.reflector_port.get()
        }
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.log(f"[!] Error saving settings: {e}", 'error')

    def update_attack_params(self, event=None):
        attack = self.attack_type.get()
        if attack in attack_types:
            params = attack_types[attack]
            self.min_delay.set(params['min_delay'])
            self.max_delay.set(params['max_delay'])
            self.packet_size.set(params['packet_size'])
            self.log(f"[*] Changed attack type to {attack}", 'info')

    def log(self, message, level='info'):
        if self.log_level.get() == 'Minimal' and level not in ('error', 'warning', 'success'):
            return
        if self.log_level.get() == 'Normal' and level == 'debug':
            return
            
        if self.log_output:
            self.log_output.configure(state='normal')
            self.log_output.insert(tk.END, message + "\n", level)
            self.log_output.see(tk.END)
            self.log_output.configure(state='disabled')

    def start_simulation(self):
        global attack_running, connection_status, threads, start_time, fake_requests_history, peak_requests, total_bandwidth
        
        if attack_running:
            self.log("[!] Attack already running.", 'warning')
            return

        try:
            target = self.target.get()
            port = self.port.get()
            if not (1 <= port <= 65535):
                raise ValueError("Port must be between 1 and 65535")
                
            try:
                socket.inet_aton(self.fake_ip.get())
            except socket.error:
                raise ValueError("Invalid fake IP address")
                
        except ValueError as e:
            self.log(f"[!] Error: {str(e)}", 'error')
            messagebox.showerror("Input Error", str(e))
            return

        # Initialize all shared variables under lock
        with lock:
            attack_running = True
            connection_status = 0
            fake_requests_history = []
            peak_requests = 0
            total_bandwidth = 0
            start_time = time.time()

        self.status_graph_val.set("Initializing attack...")
        attack_type = self.attack_type.get()
        self.log(f"[*] Starting {attack_type} attack against {self.target.get()}:{self.port.get()}", 'info')
        
        if attack_type in ['DNS Amplification', 'NTP Amplification', 'SNMP Amplification']:
            self.log(f"[*] Using reflector at {self.reflector_ip.get()}:{self.reflector_port.get()}", 'info')
            self.log(f"[*] Simulating amplification with spoofed IP: {self.fake_ip.get()}", 'info')

        def attack_thread():
            global connection_status, peak_requests, total_bandwidth
            
            attack_type = self.attack_type.get()
            packet_size = self.packet_size.get()
            
            amplification_factors = {
                'DNS Amplification': 50,
                'NTP Amplification': 100,
                'SNMP Amplification': 30
            }
            multiplier = amplification_factors.get(attack_type, 1)

            while attack_running:
                try:
                    # Split sleep into smaller intervals for responsive shutdown
                    for _ in range(10):
                        if not attack_running:
                            return
                        time.sleep(max(0.01, random.uniform(
                            self.min_delay.get()/10, 
                            self.max_delay.get()/10
                        )))
                    
                    with lock:
                        connection_status += 1
                        elapsed = int(time.time() - start_time)
                        
                        # Ensure history array is long enough
                        while len(fake_requests_history) <= elapsed:
                            fake_requests_history.append(0)
                        
                        # Update statistics
                        fake_requests_history[elapsed] += multiplier
                        peak_requests = max(peak_requests, fake_requests_history[elapsed])
                        total_bandwidth += packet_size * multiplier
                        
                        # Log progress periodically
                        if connection_status % 50 == 0 and self.log_level.get() != 'Minimal':
                            log_msg = f"[+] {connection_status} fake {attack_type} packets sent to {self.target.get()}:{self.port.get()}"
                            if multiplier > 1:
                                log_msg += f" (x{multiplier} amplification)"
                            self.log(log_msg, 'debug')
                            
                except Exception as e:
                    if attack_running:  # Only log if we didn't stop intentionally
                        self.log(f"[!] Thread error: {str(e)}", 'error')
                    break

        # Create and start threads
        threads = []
        for i in range(self.num_threads.get()):
            t = threading.Thread(target=attack_thread, daemon=True, name=f"AttackThread-{i}")
            t.start()
            threads.append(t)

        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.log("[+] Attack simulation started successfully", 'success')

    def stop_simulation(self):
        global attack_running
        if not attack_running:
            self.log("[!] No attack running to stop", 'warning')
            return
            
        attack_running = False
        self.status_graph_val.set("Attack stopped")
        self.log("[!] Attack simulation stopped", 'info')
        
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def reset_simulation(self):
        self.stop_simulation()
        global connection_status, fake_requests_history, peak_requests, total_bandwidth
        
        with lock:
            connection_status = 0
            fake_requests_history = []
            peak_requests = 0
            total_bandwidth = 0
        
        self.total_label_var.set("Total: 0")
        self.avg_label_var.set("Avg/sec: 0")
        self.peak_label_var.set("Peak/sec: 0")
        self.bandwidth_var.set("Bandwidth: 0 KB/s")
        self.status_graph_val.set("Ready")
        
        if matplotlib_available:
            self.line.set_data([], [])
            self.ax.set_xlim(0, 10)
            self.ax.set_ylim(0, 10)
            self.canvas.draw()
        
        self.log("[*] Simulation reset", 'info')

    def update_graph(self):
        if matplotlib_available and fake_requests_history:
            try:
                x = list(range(len(fake_requests_history)))
                y = fake_requests_history
                
                self.line.set_data(x, y)
                self.ax.set_xlim(0, max(10, len(x)))
                self.ax.set_ylim(0, max(10, max(y) * 1.1))  # Add 10% headroom
                self.canvas.draw()
                
            except Exception as e:
                self.log(f"[!] Graph update error: {str(e)}", 'error')

        if fake_requests_history:
            try:
                total = sum(fake_requests_history)
                elapsed = max(1, len(fake_requests_history))
                avg = total // elapsed
                current = fake_requests_history[-1] if fake_requests_history else 0
                
                bandwidth_kbs = (total_bandwidth / 1024) / elapsed if elapsed > 0 else 0
                
                self.total_label_var.set(f"Total: {total:,}")
                self.avg_label_var.set(f"Avg/sec: {avg:,}")
                self.peak_label_var.set(f"Peak/sec: {peak_requests:,}")
                self.bandwidth_var.set(f"Bandwidth: {bandwidth_kbs:,.2f} KB/s")
                self.status_graph_val.set(f"Current: {current:,} req/sec | {self.attack_type.get()}")
                
                if hasattr(self, 'graph_status'):
                    if current > peak_requests * 0.9:
                        self.graph_status.config(fg=self.get_theme_color('danger'))
                    elif current > peak_requests * 0.7:
                        self.graph_status.config(fg=self.get_theme_color('warning'))
                    else:
                        self.graph_status.config(fg=self.get_theme_color('accent'))
                    
            except Exception as e:
                self.log(f"[!] Stats update error: {str(e)}", 'error')

        self.after(1000, self.update_graph)

    def update_system_stats(self):
        try:
            if psutil_available:
                cpu_percent = psutil.cpu_percent()
                self.cpu_usage_var.set(f"CPU: {cpu_percent}%")
                
                mem = psutil.virtual_memory()
                self.mem_usage_var.set(f"RAM: {mem.percent}% ({mem.used//1024//1024}MB/{mem.total//1024//1024}MB)")
            else:
                self.cpu_usage_var.set("CPU: psutil not installed")
                self.mem_usage_var.set("RAM: psutil not installed")
            
        except Exception as e:
            self.log(f"[!] System stats error: {str(e)}", 'error')
            
        self.after(5000, self.update_system_stats)

    def export_logs(self):
        session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"dos_simulator_log_{session_time}.txt"
        
        filename = filedialog.asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialdir=os.path.expanduser("~/Downloads")
        )
        
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    logs = self.log_output.get("1.0", tk.END)
                    f.write(logs)
                    
                self.log(f"[*] Logs saved to {filename}", 'success')
                messagebox.showinfo("Export Successful", f"Logs saved to:\n{filename}")
                
            except Exception as e:
                self.log(f"[!] Error saving logs: {str(e)}", 'error')
                messagebox.showerror("Export Error", f"Failed to save logs:\n{str(e)}")

    def export_csv(self):
        session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"dos_simulator_data_{session_time}.csv"
        
        filename = filedialog.asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialdir=os.path.expanduser("~/Downloads")
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Timestamp', 'Requests', 'Attack Type'])
                    
                    for i, count in enumerate(fake_requests_history):
                        writer.writerow([i, count, self.attack_type.get()])
                    
                self.log(f"[*] Data exported to CSV: {filename}", 'success')
                messagebox.showinfo("Export Successful", f"Attack data saved to:\n{filename}")
                
            except Exception as e:
                self.log(f"[!] Error exporting CSV: {str(e)}", 'error')
                messagebox.showerror("Export Error", f"Failed to save CSV:\n{str(e)}")

    def clear_logs(self):
        self.log_output.configure(state='normal')
        self.log_output.delete("1.0", tk.END)
        self.log_output.configure(state='disabled')
        self.log("[*] Logs cleared", 'info')

    def show_settings(self):
        settings_win = tk.Toplevel(self)
        settings_win.title("Settings")
        settings_win.geometry("500x400")
        settings_win.resizable(False, False)
        
        ttk.Label(settings_win, text="Settings are automatically saved when changed").pack(pady=20)
        ttk.Button(settings_win, text="OK", command=settings_win.destroy).pack(pady=10)

    def show_help(self, event=None):
        help_text = """DoS Simulator Help

Attack Types:
- SYN Flood: Exploits TCP handshake
- UDP Flood: Overwhelms with UDP packets
- HTTP Flood: Floods with HTTP requests
- Slowloris: Keeps connections open
- ICMP Flood: Ping flood attack
- DNS/NTP/SNMP Amplification: Uses reflectors

Keyboard Shortcuts:
- Ctrl+S: Start attack
- Ctrl+Q: Stop attack
- F1: Show this help

This is for educational purposes only.
"""
        messagebox.showinfo("DoS Simulator Help", help_text)

    def show_about(self):
        about_text = """Advanced DoS Simulator v2.1

Educational tool for cybersecurity awareness.
Includes 8 different attack simulations.

Warning: For educational use only.
Unauthorized use against real systems is illegal.
"""
        messagebox.showinfo("About DoS Simulator", about_text)

    def on_close(self):
        try:
            self.stop_simulation()
            # Wait for threads to finish (with timeout)
            for t in threads:
                t.join(timeout=1.0)
            self.save_settings()
        except Exception as e:
            print(f"Cleanup error: {e}")
        finally:
            self.destroy()

if __name__ == "__main__":
    try:
        app = DoSSimulatorApp()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        try:
            app.stop_simulation()
            app.on_close()
        except:
            pass
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
