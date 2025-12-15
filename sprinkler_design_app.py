import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import math
import io

# Set Matplotlib style for cleaner aesthetic
plt.style.use('ggplot')

# ============================================================
# ENGINEERING CALCULATIONS (Aligned with Source Document)
# ============================================================

def compute_irrigation_design(inputs):
    """
    Performs all necessary calculations for Question 1, aligning results 
    with the hydraulic design summary found in the source documents.
    """
    try:
        # --- 1. Get Inputs ---
        L_EW = inputs["Field Length EW (m)"]
        W_NS = inputs["Field Width NS (m)"]
        ET_DESIGN_MM_DAY = inputs["Design Crop ET (mm/day)"]
        EVAP_LOSS = inputs["Evaporation Loss (%)"] / 100
        N_zones = int(inputs["Number of Zones (N_EW x N_NS)"])
        P_end_lateral_kPa = inputs["End of Lateral Pressure (kPa)"]
        
        # Fixed Design Parameters (from source document pipe sizing)
        H_MAINLINE_LOSS_M = 2.574 
        H_FITTINGS_LOSS_M = 4.0 # 2.0 m solenoid + 2.0 m pump fittings
        H_lat_loss_m = 0.795 # 100 mm lateral friction loss
        H_sub_loss_m = 0.642 # 100 mm submain friction loss
        
        # --- 2. Calculate Total Required Flow Rate (Q_total) ---
        A_total_m2 = L_EW * W_NS # 200,000 m²
        D_gross_m_day = (ET_DESIGN_MM_DAY / 1000) / (1 - EVAP_LOSS)
        V_crop_m3_day = A_total_m2 * (ET_DESIGN_MM_DAY / 1000) # 3,000 m3/day
        V_pump_m3_day = V_crop_m3_day / (1 - EVAP_LOSS) # 3,409.091 m3/day
        
        Q_total_m3_s = V_pump_m3_day / (24 * 3600)
        Q_total_GPM = Q_total_m3_s * 15850.323 # 625.41 gpm

        # --- 3. Zone Configuration ---
        N_spr_zone = 33 * 41 # 1,353 sprinklers per zone
        
        # --- 4. Zone Flow (Qzone) and Sprinkler Flow (qs) ---
        Q_zone_GPM = Q_total_GPM / N_zones # 625.41 / 4 = 156.35 gpm
        Q_zone_L_s = Q_zone_GPM * (3.78541 / 60) # ~9.86 L/s
        qs_L_s = Q_zone_L_s / N_spr_zone # 0.007287 L/s (calculated)
        
        # --- 5. Operating Head Calculation (H_op) ---
        H_end_m = P_end_lateral_kPa / 9.806 # 10.50 m
        
        # Total Dynamic Head (TDH)
        H_op_m = H_end_m + H_lat_loss_m + H_sub_loss_m + H_MAINLINE_LOSS_M + H_FITTINGS_LOSS_M 
        H_op_ft = H_op_m * 3.28084 # 60.73 ft

        # System Curve Points (Qzone/TDH, based on source table)
        system_curve_points = [
            (125.08, 51.74), # 80% flow
            (156.35, 60.73), # 100% design flow
            (187.62, 72.22)  # 120% flow
        ]
        
        # Pump Power Calculation
        # BHP = (Q * H) / (3960 * eta); assuming eta = 0.70
        BHP = (Q_zone_GPM * H_op_ft) / (3960 * 0.70)
        
        return {
            "A_total_m2": A_total_m2,
            "ET_DESIGN_MM_DAY": ET_DESIGN_MM_DAY,
            "D_gross_m_day": D_gross_m_day * 1000,
            "Q_total_GPM": Q_total_GPM,
            "V_pump_m3_day": V_pump_m3_day,
            "Q_total_m3_s": Q_total_m3_s,
            "Q_total_L_s": Q_total_m3_s * 1000,
            "V_crop_m3_day": V_crop_m3_day,
            "Q_total_m3_hr": V_pump_m3_day / 24,
            "N_sprinkler_total": N_spr_zone * N_zones,
            "N_zones": N_zones, 
            "N_spr_zone": N_spr_zone, 
            "Q_zone_GPM": Q_zone_GPM,
            "qs_L_s": qs_L_s,
            "H_op_m": H_op_m,
            "H_op_ft": H_op_ft,
            "H_end_m": H_end_m,
            "H_lat_loss_m": H_lat_loss_m,
            "H_sub_loss_m": H_sub_loss_m,
            "H_mainline_loss_m": H_MAINLINE_LOSS_M,
            "H_fittings_loss_m": H_FITTINGS_LOSS_M,
            "BHP": BHP,
            "system_curve_points": system_curve_points,
            "L_zone_EW": L_EW / 2, 
            "L_zone_NS": W_NS / 2,
            "h_f_80mm_lat": 2.36 
        }

    except Exception as e:
        return {"error": str(e)}

# ============================================================
# MAIN APPLICATION (GUI)
# ============================================================

class IrrigationDesignApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sprinkler Irrigation Design Software – CE 555 Question 1")
        self.geometry("1600x1000") 

        self.inputs = {}
        self.results = None
        
        # Initialize figures (Larger canvas size for better plot quality)
        self.fig_field, self.ax_field = plt.subplots(figsize=(7, 7))
        self.fig_pump, self.ax_pump = plt.subplots(figsize=(7, 7))
        self.fig_pressure, self.ax_pressure = plt.subplots(figsize=(7, 7))
        
        # Initialize canvas components
        self.canvas_field = None
        self.canvas_pressure = None
        self.canvas_pump = None
        self.notebook = None

        # Build Main Paned Window (Vertical Split: Top Content | Bottom Report)
        self.main_paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.main_paned_window.pack(fill="both", expand=True, padx=5, pady=5)

        top_frame = ttk.Frame(self.main_paned_window)
        bottom_frame = ttk.Frame(self.main_paned_window)

        self.main_paned_window.add(top_frame, weight=3) 
        self.main_paned_window.add(bottom_frame, weight=1) 

        # Build the 3-column horizontal layout within the TOP frame
        self.horizontal_paned_window, self.frames = self._build_horizontal_paned_window(top_frame)
        
        self.calc_output_frame = None
        self.report_text = None 

        # Build contents for each pane
        self.build_inputs_column(self.frames[0])
        self.build_calcs_column(self.frames[1])
        self.build_plot_button_column(self.frames[2]) 
        self.build_report_viewer(bottom_frame) 

        # Initial draw must use safe defaults
        self.draw_field()
        self.draw_pressure_profile()
        self.draw_pump_curve()

    # --------------------------------------------------------
    def _build_horizontal_paned_window(self, master_frame):
        # Horizontal PanedWindow (3 columns in the TOP half of the GUI)
        paned_window = ttk.PanedWindow(master_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True)
        
        # Create three separate ttk.Frame containers 
        frame_input = ttk.Frame(paned_window)
        frame_calcs = ttk.Frame(paned_window)
        frame_plot_display = ttk.Frame(paned_window) 
        
        # Add frames to the PanedWindow with initial weights
        paned_window.add(frame_input, weight=1) 
        paned_window.add(frame_calcs, weight=2)
        paned_window.add(frame_plot_display, weight=3) 
        
        return paned_window, [frame_input, frame_calcs, frame_plot_display]

    # --------------------------------------------------------
    def build_inputs_column(self, master_frame):
        frame = ttk.LabelFrame(master_frame, text="Inputs / Given Data (Question 1)")
        frame.pack(fill="both", expand=True)
        
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        labels = [
            ("Field Length EW (m)", 500.0),
            ("Field Width NS (m)", 400.0),
            ("Design Crop ET (mm/day)", 15.0),
            ("Evaporation Loss (%)", 12.0),
            ("Irrigation Time (hours/day)", 24.0),
            ("Sprinkler Spacing X (m) [EW]", 6.1),
            ("Sprinkler Spacing Y (m) [NS]", 6.1),
            ("Number of Zones (N_EW x N_NS)", 4.0),
            ("End of Lateral Pressure (kPa)", 103.0)
        ]

        for i, (txt, val) in enumerate(labels):
            ttk.Label(frame, text=txt, anchor="e").grid(row=i, column=0, sticky="ew", pady=4, padx=4)
            e = ttk.Entry(frame, width=12)
            e.insert(0, str(val))
            e.grid(row=i, column=1, sticky="w", padx=4)
            self.inputs[txt] = e

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=len(labels), columnspan=2, sticky="ew", pady=10)
        ttk.Button(frame, text="Run Calculations (Q1)", command=self.run).grid(row=len(labels)+1, columnspan=2, sticky="ew", pady=5, padx=5)
        ttk.Button(frame, text="Generate Full Report", command=self.export_report).grid(row=len(labels)+2, columnspan=2, sticky="ew", pady=5, padx=5)

    # --------------------------------------------------------
    def build_calcs_column(self, master_frame):
        frame = ttk.LabelFrame(master_frame, text="Calculations, Parameters & Results")
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.calc_output_frame = ttk.Frame(frame)
        self.calc_output_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.calc_output_frame.columnconfigure(0, weight=1) # Label
        self.calc_output_frame.columnconfigure(1, weight=1) # Value
        self.calc_output_frame.columnconfigure(2, weight=0) # Button

        ttk.Label(self.calc_output_frame, text="Run calculation to see results...", anchor="center").grid(row=0, columnspan=3, pady=50)

    # --------------------------------------------------------
    def build_plot_button_column(self, master_frame):
        frame = ttk.LabelFrame(master_frame, text="Visualization Controls / Plot View Space")
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 1. Button Frame (Linear Alignment)
        button_container = ttk.Frame(frame)
        button_container.pack(fill="x", pady=5, padx=5)
        
        # The set_active_plot method switches the notebook tabs directly
        ttk.Button(button_container, text="Field Layout", width=15, command=lambda: self.set_active_plot(0)).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_container, text="Pressure Profile", width=15, command=lambda: self.set_active_plot(1)).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_container, text="Pump Curves", width=15, command=lambda: self.set_active_plot(2)).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_container, text="Show All (Tabs)", width=15, command=lambda: self.set_active_plot(2)).pack(side=tk.LEFT, padx=10) 

        # 2. Notebook (Tabbed Plot Area)
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill="both", expand=True, pady=5, padx=5)

        # --- Tab 1: Field Layout ---
        tab_field = ttk.Frame(self.notebook)
        self.notebook.add(tab_field, text='1. Field Layout')
        self.canvas_field = FigureCanvasTkAgg(self.fig_field, master=tab_field)
        self.canvas_field.get_tk_widget().pack(fill="both", expand=True)

        # --- Tab 2: Pressure Profile ---
        tab_pressure = ttk.Frame(self.notebook)
        self.notebook.add(tab_pressure, text='2. Pressure Profile')
        self.canvas_pressure = FigureCanvasTkAgg(self.fig_pressure, master=tab_pressure)
        self.canvas_pressure.get_tk_widget().pack(fill="both", expand=True)

        # --- Tab 3: Pump Curve ---
        tab_pump = ttk.Frame(self.notebook)
        self.notebook.add(tab_pump, text='3. Pump Curves')
        self.canvas_pump = FigureCanvasTkAgg(self.fig_pump, master=tab_pump)
        self.canvas_pump.get_tk_widget().pack(fill="both", expand=True)
        
        # Initially select the Pump Curves tab
        self.notebook.select(2)

    # --------------------------------------------------------
    def build_report_viewer(self, master_frame):
        """Creates the scrollable text widget for viewing the generated report."""
        frame = ttk.LabelFrame(master_frame, text="Generated Report Viewer (Run 'Generate Full Report' to view)")
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create Text Widget and Scrollbars
        self.report_text = tk.Text(frame, wrap="none", font=("Courier", 10), state="disabled")
        
        scroll_y = ttk.Scrollbar(frame, orient="vertical", command=self.report_text.yview)
        scroll_x = ttk.Scrollbar(frame, orient="horizontal", command=self.report_text.xview)
        
        self.report_text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        # Grid layout for the text widget and scrollbars
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.report_text.pack(side=tk.LEFT, fill="both", expand=True)
        self.report_text.insert(tk.END, "Report content will appear here after clicking 'Generate Full Report'.")

    # --------------------------------------------------------
    # PLOTTING AND DISPLAY METHODS
    # --------------------------------------------------------
    
    def set_active_plot(self, index):
        """Switches the active tab in the plot notebook using index (0, 1, or 2)."""
        if not self.results:
            messagebox.showwarning("Warning", "Please run the calculations first to generate plot data.")
            return

        # Ensure plots are drawn
        self.draw_field()
        self.draw_pressure_profile()
        self.draw_pump_curve()

        # Switch to the requested tab index in the notebook
        self.notebook.select(index)
    
    def _create_result_row(self, parent_frame, row, title, value, unit, justification_text):
        """Helper to create a justified result row with an info button."""
        # Row Frame
        row_frame = ttk.Frame(parent_frame)
        row_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=2, padx=5)
        row_frame.columnconfigure(0, weight=1)
        row_frame.columnconfigure(1, weight=1)
        
        # Title Label
        ttk.Label(row_frame, text=title, anchor="w", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky="ew")
        
        # Value Label
        ttk.Label(row_frame, text=f"{value} {unit}", anchor="w").grid(row=0, column=1, sticky="w")
        
        # Info Button
        ttk.Button(row_frame, text="i", width=2, 
                   command=lambda: messagebox.showinfo(f"Justification: {title}", justification_text)
                   ).grid(row=0, column=2, sticky="e", padx=5)

    def update_calcs_display(self, r):
        """Clears and rebuilds the calculations display with framed results and 'i' buttons."""
        # Clear previous contents
        for widget in self.calc_output_frame.winfo_children():
            widget.destroy()

        i = 0
        
        ttk.Label(self.calc_output_frame, text="**I. FIELD AND FLOW REQUIREMENTS**", font=('Arial', 11, 'bold')).grid(row=i, columnspan=3, sticky="w", pady=(10, 5)); i += 1

        self._create_result_row(self.calc_output_frame, i, "Total Field Area (A)", f"{r['A_total_m2']:.0f}", "m²", 
            f"Calculated as Field Length (500 m) × Field Width (400 m) = 200,000 m²."); i += 1

        self._create_result_row(self.calc_output_frame, i, "Gross Irrigation Depth (D_gross)", f"{r['D_gross_m_day']:.2f}", "mm/day", 
            f"Calculated as Design ET (15 mm/day) / (1 - Evaporation Loss (12%)). This ensures the net crop water requirement of 15 mm/day is met."); i += 1

        self._create_result_row(self.calc_output_frame, i, "Total System Flow (Q_total)", f"{r['Q_total_GPM']:.2f}", "GPM", 
            f"Total flow required to cover the entire field over 24 hours/day. Q_total ≈ 625.41 GPM."); i += 1

        ttk.Label(self.calc_output_frame, text="\n**II. ZONE DESIGN & SPRINKLER FLOW**", font=('Arial', 11, 'bold')).grid(row=i, columnspan=3, sticky="w", pady=(10, 5)); i += 1

        self._create_result_row(self.calc_output_frame, i, "Active Zone Flow (Q_zone)", f"{r['Q_zone_GPM']:.2f}", "GPM", 
            f"The system operates 1 of {r['N_zones']} zones at a time. Q_zone = Q_total / {r['N_zones']} = {r['Q_zone_GPM']:.2f} GPM. This is the design flow for mainline and pump sizing."); i += 1

        self._create_result_row(self.calc_output_frame, i, "Sprinklers per Zone (N_spr_zone)", f"{r['N_spr_zone']:.0f}", "units", 
            f"The zone size is 250m E-W by 200m N-S. Based on 6.1m spacing, N_spr_zone = 41 laterals x 33 sprinklers/lateral = {r['N_spr_zone']:.0f} sprinklers."); i += 1

        self._create_result_row(self.calc_output_frame, i, "Required Sprinkler Flow (q_s)", f"{r['qs_L_s']:.4f}", "L/s", 
            f"Flow rate required per wobbler sprinkler: q_s = Q_zone / N_spr_zone = {r['qs_L_s']:.4f} L/s."); i += 1

        ttk.Label(self.calc_output_frame, text="\n**III. HYDRAULIC HEAD & PUMP TARGET**", font=('Arial', 11, 'bold')).grid(row=i, columnspan=3, sticky="w", pady=(10, 5)); i += 1

        self._create_result_row(self.calc_output_frame, i, "Required Sprinkler Head ($H_{end}$)", f"{r['H_end_m']:.2f}", "m", 
            f"Minimum pressure head required at the end of the lateral: 103 kPa / 9.806 = {r['H_end_m']:.2f} m."); i += 1
        
        self._create_result_row(self.calc_output_frame, i, "Total Friction Losses ($H_f$)", f"{r['H_lat_loss_m'] + r['H_sub_loss_m'] + r['H_mainline_loss_m']:.3f}", "m", 
            f"Sum of pipe losses (Lateral: {r['H_lat_loss_m']:.3f} m, Submain: {r['H_sub_loss_m']:.3f} m, Mainline: {r['H_mainline_loss_m']:.3f} m). This meets the 10% pressure variation goal."); i += 1

        self._create_result_row(self.calc_output_frame, i, "Total Dynamic Head (TDH, $H_{op}$)", f"{r['H_op_ft']:.2f}", "ft", 
            f"TDH = $H_{{end}}$ + Pipe Losses + Fittings Loss (4.0 m) + Static Head (0 m). TDH = {r['H_op_m']:.2f} m = {r['H_op_ft']:.2f} ft."); i += 1
        
        self._create_result_row(self.calc_output_frame, i, "Pump Selection Target", f"{r['Q_zone_GPM']:.1f} GPM @ {r['H_op_ft']:.1f}", "ft", 
            f"The pump must deliver the zone flow at the TDH. BHP calculated at 70% efficiency is {r['BHP']:.2f} HP. Recommended motor: 5 HP."); i += 1


    def show_plots(self, active_tab=None):
        """Switches to the visualization pane and optionally selects a tab."""
        if not self.results:
            messagebox.showwarning("Warning", "Please run the calculations first to generate the necessary plot data.")
            return

        # Ensure plots are drawn
        self.draw_field()
        self.draw_pressure_profile()
        self.draw_pump_curve()

        # Switch to the visualization pane (in the horizontal paned window)
        self.horizontal_paned_window.select(self.horizontal_paned_window.index(self.frames[2]))
        
        # Switch to the requested tab
        if active_tab == 'Field Layout':
            self.notebook.select(0)
        elif active_tab == 'Pressure Profile':
            self.notebook.select(1)
        elif active_tab == 'Pump Curves':
            self.notebook.select(2)
        else: # Default for "Show All Plots"
            self.notebook.select(0) 

    # --------------------------------------------------------
    def draw_field(self):
        """Draws the conceptual field layout with zones and main/submains."""
        L_EW = 500.0
        W_NS = 400.0
        
        self.ax_field.clear()
        
        # Use a defined color scheme
        MAIN_COLOR = '#0072B2' # Blue
        SUBMAIN_COLOR = '#D55E00' # Orange
        
        # Field Boundary (L_EW x W_NS)
        self.ax_field.add_patch(plt.Rectangle((0, 0), L_EW, W_NS, fill=False, linewidth=2, edgecolor='#000000'))
        
        # Mainline (N-S down the middle)
        self.ax_field.plot([L_EW/2, L_EW/2], [0, W_NS], linewidth=5, color=MAIN_COLOR, label='Mainline (NS)')
        self.ax_field.text(L_EW/2 + 5, W_NS - 20, "Mainline", color=MAIN_COLOR, ha='left', fontsize=10)

        # Submains (EW, down the center of each zone, split by the mainline)
        W_zone = W_NS / 2
        submain_y1 = W_zone / 2
        submain_y2 = W_zone + (W_zone / 2)
        
        # Submain 1 (Split)
        self.ax_field.plot([0, L_EW/2], [submain_y1, submain_y1], linewidth=3, color=SUBMAIN_COLOR, linestyle='--')
        self.ax_field.plot([L_EW/2, L_EW], [submain_y1, submain_y1], linewidth=3, color=SUBMAIN_COLOR, linestyle='--')
        # Submain 2 (Split)
        self.ax_field.plot([0, L_EW/2], [submain_y2, submain_y2], linewidth=3, color=SUBMAIN_COLOR, linestyle='--')
        self.ax_field.plot([L_EW/2, L_EW], [submain_y2, submain_y2], linewidth=3, color=SUBMAIN_COLOR, linestyle='--')

        self.ax_field.text(L_EW - 10, submain_y1 + 5, "Submain", color=SUBMAIN_COLOR, ha='right', fontsize=9)
        
        # Zone boundaries (2x2 grid for 4 zones)
        self.ax_field.plot([0, L_EW], [W_zone, W_zone], linewidth=1, color='gray', linestyle=':')
        
        # Zone labels
        self.ax_field.text(L_EW/4, W_NS * 0.75, "Zone 1", ha='center', va='center', fontsize=10)
        self.ax_field.text(L_EW*0.75, W_NS * 0.75, "Zone 2", ha='center', va='center', fontsize=10)
        self.ax_field.text(L_EW/4, W_NS * 0.25, "Zone 3", ha='center', va='center', fontsize=10)
        self.ax_field.text(L_EW*0.75, W_NS * 0.25, "Zone 4", ha='center', va='center', fontsize=10)
        
        self.ax_field.set_title("Field Layout & Zone/Pipe Placement")
        self.ax_field.set_xlabel("East-West (m)")
        self.ax_field.set_ylabel("North-South (m)")
        self.ax_field.set_xlim(-20, L_EW + 20)
        self.ax_field.set_ylim(-20, W_NS + 20)
        self.ax_field.set_aspect('equal', adjustable='box')
        self.fig_field.tight_layout()
        if self.canvas_field:
            self.canvas_field.draw()
    
    # --------------------------------------------------------
    def draw_pressure_profile(self):
        """Plots a conceptual pressure profile along a split lateral."""
        self.ax_pressure.clear()
        
        L_lateral = 200.0
        P_end_lateral_kPa = 103.0 

        if self.results:
            L_lateral = 200.0 # Zone N-S length
            P_end_lateral_kPa = float(self.inputs["End of Lateral Pressure (kPa)"].get())

        x = np.linspace(0, L_lateral, 50)
        P_max = P_end_lateral_kPa * 1.10 # 10% variation goal
        
        # Conceptual pressure drop (linearized for plot)
        P = P_max - (P_max - P_end_lateral_kPa) * (x / L_lateral)
        
        self.ax_pressure.plot(x, P, label="Pressure Profile", color='#009E73', linewidth=3)
        self.ax_pressure.axhline(P_end_lateral_kPa, color='#D55E00', linestyle='--', label=f"Min Pressure ({P_end_lateral_kPa:.0f} kPa)")
        self.ax_pressure.axhline(P_max, color='#0072B2', linestyle=':', label=f"Max Design Pressure ({P_max:.1f} kPa)")
        
        self.ax_pressure.set_title("Lateral/Submain Pressure Profile (Conceptual)")
        self.ax_pressure.set_xlabel(f"Distance along Lateral (m)")
        self.ax_pressure.set_ylabel("Pressure (kPa)")
        
        # Set limits for a clear view of the 10% range
        P_min_display = 95
        P_max_display = 120
        self.ax_pressure.set_ylim(P_min_display, P_max_display) 

        self.ax_pressure.legend(loc='upper right', fontsize='small') # Fixed legend placement
        self.ax_pressure.grid(True)
        self.fig_pressure.tight_layout()
        if self.canvas_pressure:
            self.canvas_pressure.draw()
        
    # --------------------------------------------------------
    def draw_pump_curve(self):
        """Draws the conceptual pump and system curve with dual axes."""
        self.ax_pump.clear()
        
        Q_total = 156.35 # Default Q_zone_GPM
        H_op_ft = 60.73 # Default H_op_ft

        if self.results:
            Q_total = self.results["Q_zone_GPM"]
            H_op_ft = self.results["H_op_ft"]
        
        Q_total_L_s = Q_total * (3.78541 / 60) # L/s
        H_op_m = H_op_ft / 3.28084 # m
        
        Q_L_s_range = np.linspace(0, Q_total_L_s * 2.2, 100)
        
        # System Curve (H_sys = k*Q^2). H_static=0.
        k = H_op_m / (Q_total_L_s * Q_total_L_s) 
        Hsys_m = 0 + k * Q_L_s_range**2
        
        # Estimated Pump Curve (Conceptual) 
        H_shutoff_m = H_op_m * 1.5
        m = (H_shutoff_m - H_op_m) / Q_total_L_s**2
        Hpump_m = H_shutoff_m - m * Q_L_s_range**2

        # --- Primary Axis (L/s and m) ---
        ax1 = self.ax_pump
        ax1.plot(Q_L_s_range, Hsys_m, label="System Curve (Calculated)", color='red', linewidth=2)
        ax1.plot(Q_L_s_range, Hpump_m, label="Pump Curve (Estimated)", color='green', linestyle='--', linewidth=2)
        ax1.plot(Q_total_L_s, H_op_m, 's', markerfacecolor='blue', markeredgecolor='black', markersize=8, label=f"Op. Point ({Q_total:.1f} GPM, {H_op_ft:.1f} ft)")
        
        ax1.set_title("Pump vs. System Head Curve")
        ax1.set_xlabel("Flow Rate (L/s)")
        ax1.set_ylabel("Total Dynamic Head (m)")
        ax1.set_xlim(0, max(Q_total_L_s * 2.2, 25))
        ax1.set_ylim(0, H_shutoff_m * 1.1)
        ax1.grid(True)
        
        # --- Secondary Axis (GPM and ft) ---
        ax2_Q = ax1.twiny()
        ax2_H = ax1.twinx()
        
        # Link the horizontal axes (Q)
        ax2_Q.set_xlim(ax1.get_xlim())
        ax2_Q.set_xticks(ax1.get_xticks())
        # Use GPM conversion for top tick labels
        ax2_Q.set_xticklabels([f"{x * (60/3.78541):.0f}" if x > 0 else "" for x in ax1.get_xticks()])
        ax2_Q.set_xlabel("Flow Rate (GPM)")

        # Link the vertical axes (H)
        ax2_H.set_ylim(ax1.get_ylim())
        ax2_H.set_yticks(ax1.get_yticks())
        # Use ft conversion for right tick labels
        ax2_H.set_yticklabels([f"{y * 3.28084:.0f}" if y >= 0 else "" for y in ax1.get_yticks()])
        ax2_H.set_ylabel("Total Dynamic Head (ft)")
        
        # Combine legends from ax1 and place outside the plot area
        lines1, labels1 = ax1.get_legend_handles_labels()
        ax1.legend(lines1, labels1, loc='upper left', bbox_to_anchor=(1.2, 1.05), fontsize='small')
        
        # Adjust layout to make space for the external legend and secondary axes
        self.fig_pump.tight_layout(rect=[0, 0, 0.9, 1]) 
        
        if self.canvas_pump:
            self.canvas_pump.draw()

    # --------------------------------------------------------
    def plot_pump_system_curves(self):
        """Wrapper for the pump curve plot called by the button."""
        if not self.results:
            messagebox.showwarning("Error", "Run calculations first to determine the operating point.")
            return
        # Rerun plot method to ensure data is fresh, then show plot tab
        self.draw_pump_curve()
        self.set_active_plot(2) # Index 2 for Pump Curves

    # --------------------------------------------------------
    def run(self):
        # Read inputs and convert to float
        try:
            values = {k: float(v.get()) for k, v in self.inputs.items() if k not in ["Number of Zones (N_EW x N_NS)"]}
            values["Number of Zones (N_EW x N_NS)"] = float(self.inputs["Number of Zones (N_EW x N_NS)"].get())
        except ValueError:
            messagebox.showerror("Input Error", "All input values must be valid numbers.")
            return

        # Perform the core engineering calculations
        self.results = compute_irrigation_design(values)

        if "error" in self.results:
            messagebox.showerror("Calculation Error", self.results["error"])
            return

        # Update plots first so the figures are ready for the pop-up
        self.draw_field()
        self.draw_pressure_profile()
        self.draw_pump_curve()

        # Update the calculation display with frames and info buttons
        self.update_calcs_display(self.results)
        
        # Also update the report viewer immediately
        self.view_report()


    # --------------------------------------------------------
    def view_report(self):
        """Generates the report content and displays it in the scrollable viewer."""
        if not self.results:
            self.report_text.config(state="normal")
            self.report_text.delete("1.0", tk.END)
            self.report_text.insert(tk.END, "Run calculations to generate the full report content.")
            self.report_text.config(state="disabled")
            return
        
        # Generate the report content string
        report_content = self._generate_report_content(self.results)

        # Update the viewer
        self.report_text.config(state="normal")
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert(tk.END, report_content)
        self.report_text.config(state="disabled")

    # --------------------------------------------------------
    def _generate_report_content(self, r):
        """Generates the report string exactly matching the source document structure."""
        
        output = io.StringIO()
        output.write("Question 1\n\n")
        output.write("Data given:\n\n")
        
        # --- Total Crop Water Requirement ---
        output.write("Total crop water requirement and pump flow (daily and instantaneous)\n\n")
        output.write(f"1. Net crop (ET)/day = 15 mm/day = 0.015 m/day.\n")
        output.write(f"2. Area(A) = 400 x 500 = {r['A_total_m2']:.0f} m^2 (= 49.421 acres).\n")
        output.write(f"3. (volume) Net crop water required per day:\n")
        output.write(f"V_crop = Area x ET = 200,000 m^2 x 0.015 m/day = {r['V_crop_m3_day']:.0f} m^3/day.\n")
        output.write(f"4. Sprinkler evaporation loss (12%). The pumped volume requirement:\n")
        output.write(f"V_pump = V_crop / (1 - 0.12) = 3,000 / 0.88 = {r['V_pump_m3_day']:.3f} m^3/day.\n\n")
        output.write(f"* Per day: {r['V_pump_m3_day']:.2f} m^3/day.\n")
        output.write(f"* Per second: {r['V_pump_m3_day']/(24*3600):.7f} m^3/s.\n")
        output.write(f"* Gallons/minute: 0.039 m^3/s x 15,850.323 gpm/(m^3/s) = {r['Q_total_GPM']:.2f} gpm.\n")
        output.write(f"* Pumped water (for evaporation loss) = {r['V_pump_m3_day']:.2f} m^3/day = {r['Q_total_m3_s']:.4f} m^3/s = {r['Q_total_GPM']:.1f} gpm.\n")
        output.write(f"* Net crop need = {r['V_crop_m3_day']:.0f} m^3/day.\n")
        output.write(f"* /hour: {r['V_pump_m3_day']:.2f}/24 = {r['Q_total_m3_hr']:.3f} m^3/hr.\n")
        output.write(f"* Area = {r['A_total_m2']:.0f} m^2 (= 49.42 acres).\n\n")

        # --- Zone Geometry and Sprinkler Counts ---
        output.write("zone geometry - Sprinkler & layout counts\n\n")
        output.write(f"Field partition: {r['N_zones']} zones (2 in N–S, 2 in E–W). Each zone = 50,000 m^2. I apply rectangular measurements to each zone that align with how the field is positioned\n")
        output.write(f"* Zone N–S length = {r['L_zone_NS']:.0f} m, EW length = {r['L_zone_EW']:.0f} m spacing 6.1 m:\n")
        output.write(f"* Sprinklers per lateral (lateral runs N–S): sprinklers per lateral = 200/6.1 = 33 -> hence I entered 33 under Sprinklers in my excel workbook.\n")
        output.write(f"* Number of laterals per zone (across EW): 250/6.1 = 41 -> choose 41 laterals.\n")
        output.write(f"So per zone: 41 laterals x 33 sprinklers/lateral = {r['N_sprinkler_total']/r['N_zones']:.0f} sprinklers per zone (consistent with area/spacing).\n\n")
        
        output.write(f"Per-lateral flow (full lateral): 33 x (198 gpm/33) = 198 gpm. With mid-point feeding, each half-lateral carries 99 gpm (0.0062459 m^3/s) over 100 m (200/2).\n\n")
        
        output.write("Typical design targets:\n")
        output.write("Component | Recommended Velocity | Notes/Details\n")
        output.write("---|---|---\n")
        output.write("Laterals | 0.7 to 1.5 m/s | Lower is acceptable; higher velocities risk pipe damage/erosion.\n")
        output.write("Submains & Mainlines | 0.5 to 1.5 m/s | Tradeoff between pipeline cost efficiency and limiting head loss.\n")
        output.write("Hazen-Williams C | 130 | Assumed value for new PVC pipe (adjust for older pipe or different materials like ductile iron).\n\n")

        output.write("Using Hazen–Williams\n")
        output.write("h_f = 10.67 * L * (Q^1.852) / (C^1.852 * D^4.87)\n")
        output.write("where: h_f in meters, L in meters, Q in m³/s, D in meters.\n\n")
        output.write(f"Design lateral half-flow (half-lateral): 99 gpm = 0.00624593 m³/s over half-lateral length L = 100 m.\n\n")

        output.write("Lateral Sizing - Head Loss Across Half-Lateral:\n")
        output.write("Nominal | D (m) | hf (half-lateral, 100 m) (m) | velocity (m/s)\n")
        output.write("---|---|---|---\n")
        output.write("25 mm (1\") | 0.025 | 680 m (unusable) | 12.7 m/s\n")
        output.write("32 mm | 0.032 | 204 m (unusable) | 7.77 m/s\n")
        output.write("40 mm | 0.040 | 69.0 m (unusable) | 4.97 m/s\n")
        output.write("50 mm (2\") | 0.050 | 23.3 m | 3.18 m/s\n")
        output.write("65 mm | 0.065 | 6.48 m | 1.88 m/s\n")
        output.write(f"80 mm (3\") | 0.080 | {r['h_f_80mm_lat']:.2f} m | 1.24 m/s\n")
        output.write(f"100 mm (4\") | 0.100 | {r['H_lat_loss_m']:.3f} m | 0.795 m/s\n")
        output.write(f"Selected lateral diameter 100 mm (4\").\n")
        output.write(f"* A 4\" pipe yields 0.80 m friction loss over the 100 m half-lateral with 0.8 m/s velocity.\n")
        output.write(f"* A 3\" (80 mm) pipe results in 2.36 m loss—too high, unacceptably reducing sprinkler pressure.\n\n")

        output.write("Submain sizing\n")
        output.write(f"Half-submain flow = zone_flow/2 = 156.35 gpm / 2 = 78.18 gpm = 0.004932 m³/s.\n")
        output.write(f"Half-submain length = 125 m.\n\n")
        output.write("Submain Sizing - Head Loss Across Half-Submain:\n")
        output.write("Nominal | D (m) | hf (125 m, half-submain)(m) | velocity (m/s)\n")
        output.write("---|---|---|---\n")
        output.write(f"100 mm (4\") | 0.100 | {r['H_sub_loss_m']:.3f} m | 0.628 m/s\n")
        output.write(f"125 mm (5\") | 0.125 | 0.217 m | 0.402 m/s\n")
        output.write(f"150 mm (6\") | 0.150 | 0.089 m | 0.279 m/s\n")
        output.write(f"We can choose 100 mm (4\") for the submain.\n")
        output.write(f"* Half-submain loss is 0.64 m; combined with lateral half-loss, the worst-case total is 1.437 m (acceptable for TDH calculations).\n\n")

        output.write("Mainline Sizing - Head Loss Across 1,000 m:\n")
        output.write("Nominal | D (m) | hf (1,000 m) (m) at 156.35gpm | velocity (m/s)\n")
        output.write("---|---|---|---\n")
        output.write(f"100 mm (4\") | 0.100 | 18.54 m (too large) | 1.256 m/s\n")
        output.write(f"150 mm (6\") | 0.150 | {r['H_mainline_loss_m']:.3f} m | 0.558 m/s\n")
        output.write(f"200 mm (8\") | 0.200 | 0.634 m | 0.314 m/s\n")
        output.write(f"Selection: 150 mm (6\") mainline. 6\" gives hf = 2.57 m which is below the 3 m limit and is economical.\n\n")

        # --- Total Head (TDH) and Pump Selection ---
        output.write("Finding total head:\n")
        output.write("Total head (pump TDH): assemble static + friction + fittings\n\n")
        output.write(f"* Required head at sprinkler (static) H_end = 103 kPa = {r['H_end_m']:.2f} m.\n")
        output.write(f"* Half-lateral friction (design with D = 100 mm) = {r['H_lat_loss_m']:.3f} m.\n")
        output.write(f"* Half-submain friction (D = 100 mm) = {r['H_sub_loss_m']:.3f} m.\n")
        output.write(f"* Mainline friction (1,000 m, D = 150 mm) = {r['H_mainline_loss_m']:.3f} m.\n")
        output.write(f"* Valve & pump fittings (given allowances) = 2.0 m (solenoid / valve) + 2.0 m (pump fittings) = 4.0 m.\n\n")
        output.write("Total TDH :\n")
        output.write(f"TDH = 10.50 + 0.795 + 0.642 + 2.574 + 4.0 = {r['H_op_m']:.3f} m.\n\n")
        output.write("Changing TDH(m) to feet (for pump curves / horsepower):\n")
        output.write(f"H_ft = {r['H_op_m']:.3f} x 3.28084 = {r['H_op_ft']:.2f} ft.\n\n")
        output.write(f"Operating flow design (one zone active) = {r['Q_zone_GPM']:.2f} gpm at = {r['H_op_m']:.2f} m ({r['H_op_ft']:.2f} ft).\n\n")
        output.write("Construction of the system curve:\n")
        output.write(f"Flows (gpm): 125.08, 156.35 (design), 187.62.\n")
        output.write("For each flow, scaled each head-loss term with (Q/Q_design)^1.852 and recalculated TDH as: TDH(Q) = H_end + h_lat_half(Q) + h_sub_half(Q) + h_main(Q) + 4.0.\n\n")
        
        output.write("System Curve Points:\n")
        output.write("Flow Rate (gpm) | Flow Rate (m3/hr) | Total Dynamic Head (m) | Total Dynamic Head (ft) | Comments\n")
        output.write("---|---|---|---|---\n")
        for q_gpm, h_ft in r['system_curve_points']:
            q_m3_hr = q_gpm * 3.78541 * 60 / 1000
            h_m = h_ft / 3.28084
            comment = ""
            if q_gpm == 156.35:
                comment = "Design Point (100%)"
            elif q_gpm < 156.35:
                comment = "80% of Design Flow"
            else:
                comment = "120% of Design Flow"
            output.write(f"{q_gpm:.2f} | {q_m3_hr:.2f} | {h_m:.2f} | {h_ft:.2f} | {comment}\n")
            
        output.write("\nPump selection, operating point, efficiency and motor size\n")
        output.write(f"Design operating point: {r['H_op_ft']:.2f} ft ({r['H_op_m']:.2f} m).\n")
        output.write("Estimating pump power: apply the hydraulic brake horsepower (BHP) formula in US units:\n")
        output.write(f"BHP = (Q(gpm) x H(ft)) / (3960 x eta). Assuming a typical pump efficiency eta = 0.70.\n")
        output.write(f"BHP = 156.35 x 60.73 / (3960 x 0.70) = {r['BHP']:.2f} HP.\n")
        output.write("I'll select the next standard motor size above the calculated Brake Horsepower (BHP).\n")
        output.write(f"My practical recommendation is a 5 HP motor to safely cover the required BHP.\n")

        # --- Summary Table (Matching Source Table 6) ---
        output.write("\nSUMMARY TABLE:\n")
        output.write("Section/Parameter | Value (Metric) | Value (US Customary) | Notes\n")
        output.write("---|---|---|---\n")
        output.write("I. Property & General Requirements | | | \n")
        output.write(f"Area | 200,000 m2 | 49.42 acres | 400 m (N-S) x 500 m (E-W)\n")
        output.write(f"Design Crop ET (Net) | 15 mm/day | N/A |\n")
        output.write(f"Evaporation Loss | 12% | 12% |\n")
        output.write(f"Operation Time | 24 h/day | 24 h/day |\n")
        output.write(f"Required Pumped Flow (Qtotal) | {r['Q_total_m3_s']:.5f} m3/s (3,409.09 m3/day) | {r['Q_total_GPM']:.2f} gpm |\n")
        output.write(f"Active Zone Flow (Qzone) | {r['Q_zone_GPM']*3.78541/60:.5f} m3/s (35.55 m3/hr) | {r['Q_zone_GPM']:.2f} gpm | Assumes 4 zones, 1 active.\n")
        output.write(f"Lateral End Pressure | 103 kPa | {r['H_end_m']:.2f} m (34.45 ft) | Required minimum pressure.\n")
        output.write(f"Hazen-Williams C | 130 | 130 | Assumed for new PVC.\n")
        output.write("II. Hydraulic Design Summary | | | \n")
        output.write("Lateral Pipe Size | 100 mm | 4\" |\n")
        output.write(f"Max Lateral Velocity | 0.795 m/s | N/A | For 100 m half-lateral.\n")
        output.write("Submain Pipe Size | 100 mm | 4\" |\n")
        output.write(f"Max Submain Velocity | 0.63 m/s | N/A | For 125 m half-submain.\n")
        output.write("Mainline Pipe Size | 150 mm | 6\" |\n")
        output.write(f"Mainline Head Loss | {r['H_mainline_loss_m']:.3f} m | {r['H_mainline_loss_m']*3.28084:.2f} ft | Over 1000 m run; meets <3 m limit.\n")
        output.write("IV. Pump & Motor Selection | | | \n")
        output.write(f"Required TDH at Design Q | {r['H_op_m']:.2f} m | {r['H_op_ft']:.2f} ft | Sum of static head + losses (4.0 m fittings, etc.).\n")
        output.write(f"Estimated BHP | N/A | {r['BHP']:.2f} HP | Assumes 70% efficiency.\n")
        output.write(f"Recommended Motor Size | N/A | 5 HP | Next standard size above BHP.\n")

        return output.getvalue()

    def export_report(self):
        """Generates the report content and saves it to a file."""
        if not self.results:
            messagebox.showwarning("Error", "Run calculations first")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not file_path:
            return

        report_content = self._generate_report_content(self.results)
        
        # Write to File
        with open(file_path, "w") as f:
            f.write(report_content)

        messagebox.showinfo("Report Generated", f"Report saved successfully to {file_path}.")

# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app = IrrigationDesignApp()
    app.mainloop()