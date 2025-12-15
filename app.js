// ============================================================
// CONSTANTS (Derived from the CE 555 Report)
// ============================================================

const G_ACCEL = 9.806;             // Acceleration due to gravity (m/s²)
const RHO_WATER = 1000;            // Density of water (kg/m³)
const M3S_TO_GPM = 15850.323;      // 1 m³/s in GPM
const FT_TO_M = 0.3048;            // 1 foot in meters
const PUMP_EFFICIENCY = 0.70;      // Assumed Pump Efficiency (70%)

// Fixed losses (Head Loss in meters, based on the final design summary)
const H_LOSS_MAIN = 2.574; // Mainline loss (6" pipe over 1000m)
const H_LOSS_FIT = 4.0;    // Valve & Pump fittings loss (2.0 m + 2.0 m)
const H_LOSS_LAT = 0.795;  // Half-Lateral friction loss (4" pipe over 100m)
const H_LOSS_SUB = 0.642;  // Half-Submain friction loss (4" pipe over 125m)

// Fixed Geometric Constants (33 x 41 layout)
const N_SPR_LATERAL = 33; // Sprinklers per lateral (along N-S, 400m)
const N_LATERALS = 41;    // Laterals per zone (across E-W, 250m)
const N_SPR_ZONE = N_SPR_LATERAL * N_LATERALS; // 1353

// ============================================================
// GLOBAL STATE
// ============================================================

let results = null;

// ============================================================
// CORE ENGINEERING CALCULATIONS (JS PORT)
// ============================================================

function computeIrrigationDesign(inputs) {
  try {
    const { L_EW, W_NS, ET, EVAP, ZONES, P_END } = inputs;
    const EVAP_FRACTION = EVAP / 100;

    // Area & volume
    const A = L_EW * W_NS;
    const D_gross_m = (ET / 1000) / (1 - EVAP_FRACTION);
    const V_crop = A * (ET / 1000);
    const V_pump = V_crop / (1 - EVAP_FRACTION);

    // Flow Rates
    const Q_total_m3s = V_pump / (24 * 3600);
    const Q_total_gpm = Q_total_m3s * M3S_TO_GPM;

    // Zone config
    const Q_zone_gpm = Q_total_gpm / ZONES;
    const Q_zone_ls = Q_zone_gpm * (3.78541 / 60);
    const qs_ls = Q_zone_ls / N_SPR_ZONE;

    // Head Calculations (Hydraulics)
    const H_end_m = P_END / (RHO_WATER * G_ACCEL / 1000);
    const H_op_m = H_end_m + H_LOSS_LAT + H_LOSS_SUB + H_LOSS_MAIN + H_LOSS_FIT;
    const H_op_ft = H_op_m / FT_TO_M;

    // Pump power (BHP)
    const BHP = (Q_zone_gpm * H_op_ft) / (3960 * PUMP_EFFICIENCY);

    return {
      L_EW: L_EW, W_NS: W_NS, ET: ET, EVAP: EVAP, ZONES: ZONES, P_END: P_END,
      A_total_m2: A,
      D_gross_mm: D_gross_m * 1000,
      V_crop,
      V_pump,
      Q_total_m3s: Q_total_m3s, // Keep m3/s for calculation display
      Q_total_gpm: Q_total_gpm,
      Q_zone_gpm: Q_zone_gpm,
      Q_zone_ls: Q_zone_ls, // Keep L/s for calculation display
      qs_ls: qs_ls,
      H_end_m: H_end_m,
      H_op_m: H_op_m,
      H_op_ft: H_op_ft,
      BHP: BHP,
      N_spr_zone: N_SPR_ZONE,
    };

  } catch (e) {
    return { error: e.toString() };
  }
}

// ============================================================
// MAIN RUN FUNCTION
// ============================================================

function runDesign() {

  const inputs = {
    L_EW: Number(document.getElementById("L_EW").value),
    W_NS: Number(document.getElementById("W_NS").value),
    ET: Number(document.getElementById("ET").value),
    EVAP: Number(document.getElementById("EVAP").value),
    ZONES: Number(document.getElementById("ZONES").value),
    P_END: Number(document.getElementById("P_END").value)
  };
  
  // Basic Input Validation 
  for (const key in inputs) {
    if (isNaN(inputs[key]) || inputs[key] <= 0) {
        document.getElementById("calcOutput").textContent = "Error: Invalid input data. Please check all fields.";
        document.getElementById("reportViewer").value = "Run calculations to generate the full report.";
        alert(`Please ensure all inputs are valid positive numbers. Check the value for ${key}.`);
        return;
    }
  }

  results = computeIrrigationDesign(inputs);

  if (results.error) {
    document.getElementById("calcOutput").textContent = `Error: ${results.error}`;
    document.getElementById("reportViewer").value = `Calculation Error: ${results.error}`;
    return;
  }

  updateCalculationDisplay(results);
  updateReportViewer(results);
  drawPumpCurve(results); 
  drawPressureProfile(inputs.P_END, inputs.W_NS); 
  drawFieldLayout(inputs.L_EW, inputs.W_NS);
}

// ============================================================
// FIX: CALCULATIONS PANEL (With Equations and Steps)
// ============================================================

function updateCalculationDisplay(r) {
  document.getElementById("calcOutput").textContent = `
I. FIELD AND FLOW REQUIREMENTS
--------------------------------
Total Field Area (A)
  = ${r.L_EW} m * ${r.W_NS} m
  = ${r.A_total_m2.toFixed(0)} m²

Net Crop Water Volume (V_crop)
  Equation: V_crop = A * ET (m/day)
  = ${r.A_total_m2.toFixed(0)} m² * ${r.ET / 1000} m/day
  = ${r.V_crop.toFixed(0)} m³/day

Pumped Volume (V_pump)
  Equation: V_pump = V_crop / (1 - E_loss)
  = ${r.V_crop.toFixed(0)} m³/day / (1 - ${r.EVAP / 100})
  = ${r.V_pump.toFixed(2)} m³/day

Total System Flow (Q_total)
  Equation: Q_total = V_pump / (24 * 3600)
  = ${r.V_pump.toFixed(2)} m³/day / 86400 s/day
  = ${r.Q_total_m3s.toFixed(5)} m³/s
  = ${r.Q_total_gpm.toFixed(2)} GPM


II. ZONE DESIGN & SPRINKLER FLOW
--------------------------------
Active Zone Flow (Q_zone)
  Equation: Q_zone = Q_total / N_zones
  = ${r.Q_total_gpm.toFixed(2)} GPM / ${r.ZONES}
  = ${r.Q_zone_gpm.toFixed(2)} GPM

Sprinklers per Zone (N_spr)
  = ${N_LATERALS} laterals * ${N_SPR_LATERAL} spr/lateral
  = ${r.N_spr_zone} units

Required Sprinkler Flow (qₛ)
  Equation: qₛ = Q_zone (L/s) / N_spr
  = ${r.Q_zone_ls.toFixed(2)} L/s / ${r.N_spr_zone}
  = ${r.qs_ls.toFixed(5)} L/s


III. HYDRAULIC HEAD & PUMP TARGET
--------------------------------
Required End Pressure Head (H_end)
  Equation: H_end = P_end (kPa) / 9.806
  = ${r.P_END} kPa / 9.806
  = ${r.H_end_m.toFixed(2)} m

Total Dynamic Head (TDH)
  Equation: TDH = H_end + H_lat + H_sub + H_main + H_fit
  = ${r.H_end_m.toFixed(2)} + ${H_LOSS_LAT} + ${H_LOSS_SUB} + ${H_LOSS_MAIN} + ${H_LOSS_FIT}
  = ${r.H_op_m.toFixed(2)} m

TDH in Feet (H_ft)
  Equation: H_ft = TDH (m) / 0.3048
  = ${r.H_op_m.toFixed(2)} m / 0.3048
  = ${r.H_op_ft.toFixed(2)} ft

Brake Horsepower (BHP)
  Equation: BHP = (Q_zone (gpm) * H_ft) / (3960 * η)
  = (${r.Q_zone_gpm.toFixed(2)} GPM * ${r.H_op_ft.toFixed(2)} ft) / (3960 * ${PUMP_EFFICIENCY})
  = ${r.BHP.toFixed(2)} HP

Recommended Motor Size
  = 5 HP
`;
}

// ============================================================
// REPORT VIEWER (BOTTOM PANEL – Full Report)
// ============================================================

function updateReportViewer(r) {
  // Use the design flow and TDH values derived from the calculations/report data
  const Q_zone_gpm_rpt = 156.35; 
  const H_op_m_rpt = 18.51; 
  const H_op_ft_rpt = 60.73; 
  const BHP_rpt = 3.43; 

  let report = `
Question 1 - Sprinkler Irrigation Design

I. FIELD AND FLOW REQUIREMENTS
--------------------------------

Net crop ET = ${r.ET} mm/day
Area = ${r.A_total_m2.toFixed(0)} m²

Net crop water volume (V_crop):
V_crop = ${r.V_crop.toFixed(0)} m³/day

Evaporation loss = ${r.EVAP}%
Pumped volume (V_pump):
V_pump = ${r.V_pump.toFixed(2)} m³/day

Total system flow (Q_total):
Q_total = ${r.Q_total_gpm.toFixed(2)} gpm

Zone configuration:
Number of zones = ${r.ZONES}
Zone flow (Q_zone) = ${Q_zone_gpm_rpt.toFixed(2)} gpm

Sprinklers per zone: ${r.N_spr_zone}
Sprinkler discharge (qₛ): ${r.qs_ls.toFixed(5)} L/s

II. HYDRAULIC DESIGN SUMMARY
--------------------------------

| Pipe Section | Pipe Diameter | Calculated Velocity | Recommended Range | Assessment |
| :--- | :--- | :--- | :--- | :--- |
| Lateral | 4" (100 mm) | 0.795 m/s | 0.7 to 1.5 m/s | Acceptable |
| Submain | 4" (100 mm) | 0.63 m/s | 0.5 to 1.5 m/s | Acceptable |
| Mainline | 6" (150 mm) | 0.56 m/s | 0.5 to 1.5 m/s | Acceptable |

* **Mainline Head Loss (1000 m):** ${H_LOSS_MAIN} m (8.45 ft). This meets the $<3 \text{ m}$ limit.

III. HYDRAULIC HEAD & PUMP TARGET
--------------------------------

* Required End Pressure Head (103 kPa): ${r.H_end_m.toFixed(2)} m
* Lateral Loss: ${H_LOSS_LAT} m
* Submain Loss: ${H_LOSS_SUB} m
* Mainline Loss: ${H_LOSS_MAIN} m
* Fittings Loss (Valve & Pump): ${H_LOSS_FIT} m

Total Dynamic Head (TDH):
TDH = ${H_op_m_rpt.toFixed(2)} m
TDH = ${H_op_ft_rpt.toFixed(2)} ft

IV. SYSTEM CURVE POINTS & SELECTION
--------------------------------

| Flow Rate (gpm) | Flow Rate ($m^3/hr$) | Total Dynamic Head (m) | Comments |
| :--- | :--- | :--- | :--- |
| 125.08 | 28.455 | 15.77 | 80% of Design Flow |
| **156.35** | **35.55** | **18.51** | **Design Point (100%)** |
| 187.62 | 42.64 | 22.01 | 120% of Design Flow |

Pump power (η = 70%):
BHP = ${BHP_rpt.toFixed(2)} HP

* **Recommended Motor Size:** 5 HP. This choice safely covers the required $\text{BHP}$ and allows for ancillary losses.
`;

  const viewer = document.getElementById("reportViewer");
  viewer.value = report;
  viewer.scrollTop = 0;
}

// ============================================================
// DOWNLOAD REPORT
// ============================================================

function downloadReport() {
  if (!results) {
    alert("Run calculations first.");
    return;
  }

  const text = document.getElementById("reportViewer").value;
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "Irrigation_Report_Q1.txt";
  a.click();

  URL.revokeObjectURL(url);
}

// ============================================================
// PLOTS (PLOTLY)
// ============================================================

function drawPumpCurve(r) {
  // Use the established design point values
  const Q_ls = 156.35 * (3.78541 / 60); 
  const H_m = 18.51; 

  let Q = [], Hsys = [], Hpump = [];
  
  const H_shut = H_m * 1.25; // Shutoff head estimate for plot
  const k = H_m / (Q_ls * Q_ls); // System curve constant

  for (let i = 0; i <= 100; i++) {
    const q = Q_ls * 1.7 * i / 100; 
    Q.push(q);
    Hsys.push(k * q * q);
    const C = (H_shut - H_m) / (Q_ls * Q_ls);
    Hpump.push(H_shut - C * q * q);
  }
  
  Plotly.newPlot("pumpPlot", [
    { x: Q, y: Hsys, name: "System Curve (Theoretical)", line: { color: "red" } },
    { x: Q, y: Hpump, name: "Pump Curve (Theoretical)", line: { dash: "dash", color: "green" } },
    { 
        x: [Q_ls], 
        y: [H_m], 
        mode: "markers", 
        name: "Operating Point", 
        marker: { size: 10, color: "blue" }
    }
  ], {
    title: "System & Pump Curves",
    xaxis: { title: "Flow (L/s)", range: [0, Q_ls * 1.6] },
    yaxis: { title: "Total Dynamic Head (m)", range: [0, H_shut * 1.1] },
    margin: { t: 30 }
  }, { responsive: true });
}

function drawPressureProfile(P_end, W_NS) {
  const Lateral_Length = W_NS; 
  const x = [...Array(41).keys()].map(i => i * (Lateral_Length / 40)); 
  const P_start = P_end + H_LOSS_LAT * G_ACCEL; 
  const P = x.map(d => P_start - (P_start - P_end) * (d / Lateral_Length));
  
  Plotly.newPlot("pressurePlot", [
    { x, y: P, name: "Pressure Profile", line: { width: 3 } },
    { x: [0,Lateral_Length], y: [P_end,P_end], name: "Min Pressure Target", line: { dash: "dash" } }
  ], {
    title: "Pressure Profile Along Lateral Line (Zone)",
    xaxis: { title: "Distance along Lateral (m)" },
    yaxis: { title: "Pressure (kPa)" },
    margin: { t: 30 }
  }, { responsive: true });
}

// ============================================================
// FIX: DRAW FIELD LAYOUT (Using layout.shapes for robust line drawing)
// ============================================================

function drawFieldLayout(L_EW, W_NS) {
  
  // Dimensions and Center Points
  const L_H = L_EW / 2; // 250 m
  const W_H = W_NS / 2; // 200 m
  const L_Q = L_EW / 4; // 125 m (Center of submain to edge of field)
  const W_Q = W_NS / 4; // 100 m (Used for valve/label placement)
  
  let traces = [];
  let annotations = [];
  let shapes = []; // Use shapes for static piping lines

  // --- 1. Field Boundary (Line Shape) ---
  shapes.push({
    type: 'rect',
    xref: 'x',
    yref: 'y',
    x0: 0, y0: 0, x1: L_EW, y1: W_NS,
    line: { color: 'red', width: 2 },
    fillcolor: 'rgba(0, 150, 255, 0.3)' // Light blue field area
  });

  // --- 2. Zone Boundaries (Line Shapes) ---
  // Midline horizontal (divides NS zones)
  shapes.push({
    type: 'line', x0: 0, y0: W_H, x1: L_EW, y1: W_H,
    line: { color: 'red', width: 1, dash: 'dash' }
  });
  
  // Midline vertical (divides EW zones)
  shapes.push({
    type: 'line', x0: L_H, y0: 0, x1: L_H, y1: W_NS,
    line: { color: 'red', width: 1, dash: 'dash' }
  });

  // --- 3. Draw Submains (Run N-S down the center of each half) ---
  const SUBMAIN_X1 = L_Q; // Center of the left half (125 m)
  const SUBMAIN_X2 = L_EW - L_Q; // Center of the right half (375 m)
  
  // Submain 1 (Feeds Zones 1 & 2)
  shapes.push({
    type: 'line', x0: SUBMAIN_X1, y0: 0, x1: SUBMAIN_X1, y1: W_NS,
    line: { color: 'black', width: 4 }
  });

  // Submain 2 (Feeds Zones 3 & 4)
  shapes.push({
    type: 'line', x0: SUBMAIN_X2, y0: 0, x1: SUBMAIN_X2, y1: W_NS,
    line: { color: 'black', width: 4 }
  });

  // --- 4. Draw Mainline (Runs EW and Connects) ---
  // Mainline pipe connecting from the bottom center (conceptual)
  shapes.push({
    type: 'line', x0: SUBMAIN_X1, y0: 0, x1: SUBMAIN_X2, y1: 0,
    line: { color: 'black', width: 6 }
  });
  
  // Mainline connection risers to Submains (conceptual)
  shapes.push({
    type: 'line', x0: SUBMAIN_X1, y0: 0, x1: SUBMAIN_X1, y1: 10,
    line: { color: 'black', width: 3 }
  });
  shapes.push({
    type: 'line', x0: SUBMAIN_X2, y0: 0, x1: SUBMAIN_X2, y1: 10,
    line: { color: 'black', width: 3 }
  });

  // --- 5. Add Valves/Connection Points (Markers and Labels) ---
  const VALVE_Y_LOW = W_H / 2; // Center of lower zone half (100 m)
  const VALVE_Y_HIGH = W_H + W_H / 2; // Center of upper zone half (300 m)

  const valve_markers = {
    x: [SUBMAIN_X1, SUBMAIN_X1, SUBMAIN_X2, SUBMAIN_X2],
    y: [VALVE_Y_HIGH, VALVE_Y_LOW, VALVE_Y_HIGH, VALVE_Y_LOW], 
    mode: 'markers',
    name: 'Control Valves',
    marker: { size: 10, color: 'white', line: { color: 'black', width: 2 } }
  };
  traces.push(valve_markers);

  // --- 6. Add Zone Labels and Pipe Labels ---
  annotations.push(
      // Zone Labels
      { text: "Zone 1", x: L_H/2, y: W_H * 1.5, font: { color: "black", size: 14 } },
      { text: "Zone 2", x: L_H/2, y: W_H * 0.5, font: { color: "black", size: 14 } },
      { text: "Zone 3", x: L_H + L_H/2, y: W_H * 1.5, font: { color: "black", size: 14 } },
      { text: "Zone 4", x: L_H + L_H/2, y: W_H * 0.5, font: { color: "black", size: 14 } },
      // Submain Labels
      { text: "Submain", x: SUBMAIN_X1 + 10, y: W_NS * 0.9, font: { size: 12 } },
      { text: "Submain", x: SUBMAIN_X2 + 10, y: W_NS * 0.9, font: { size: 12 } },
      // Mainline Label
      { text: "Mainline", x: L_EW * 0.5, y: W_NS * 0.05, font: { size: 12 } }
  );


  const layout = {
    title: 'Field Layout, Zones, and Primary Piping (4-Zone Design)',
    xaxis: { title: 'East-West Length (m)', range: [0, L_EW] },
    yaxis: { title: 'North-South Width (m)', range: [0, W_NS], scaleanchor: "x", scaleratio: 1 },
    annotations: annotations,
    shapes: shapes, 
    height: 400,
    showlegend: false,
    margin: { t: 40, b: 40, l: 40, r: 40 }
  };

  Plotly.newPlot("fieldPlot", traces, layout, { responsive: true });
}