#AI created the file 
#Author: Gemini, Johannes Kalliauer
#Copyright,License: GPLv3
#Create-Date: 2026-11-21

#Last changes:
#YYYY-MM-DD HH:mmCEST Author:      Changes
#2026-11-21 14:16 CET Gemini:      "PyNite" to "Pynite"
#2026-11-22 10:26 CET J.Kalliauer: Correction of gemini: Beding about the weak axis is not in in z-Direction, it is around the weak axis (distinglish between cross-sectoin and stucture)
#2026-11-22 10:31 CET Gemini:      Translated to English

from Pynite import FEModel3D

# ==============================================================================
# 1. Initialize model (unit system: kN, m)
# ==============================================================================
model = FEModel3D()

# Span [m]
L = 8.0

# ==============================================================================
# 2. Define nodes
# ==============================================================================
# N1: Left support (x = 0)
# N2: Right support (x = 8.0 m)
model.add_node("N1", 0.0, 0.0, 0.0)
model.add_node("N2", L, 0.0, 0.0)

# ==============================================================================
# 3. Define material: Structural steel S235 / S355 (EN 1993-1-1)
# ==============================================================================
E = 210e6      # Modulus of elasticity: 210,000 N/mm² = 210e6 kN/m²
G = 80.77e6    # Shear modulus:         80,770 N/mm² = 80.77e6 kN/m²
nu = 0.3       # Poisson's ratio [-]
rho = 78.5     # Specific weight [kN/m³]

model.add_material("Stahl", E, G, nu, rho)

# ==============================================================================
# 4. Define cross-section: HEB 300 (EN 10365 / DIN 1025-2)
# ==============================================================================
# Standard values HEB 300 (h = 300 mm, b = 300 mm, tw = 11 mm, tf = 19 mm, r = 27 mm):
# A  = 149.1 cm²   = 1.491e-2 m²
# Iy = 25170 cm⁴   = 2.517e-4 m⁴  (strong axis -> in PyNite bending about local y-axis = global z-axis!)
# Iz = 8563 cm⁴    = 8.563e-5 m⁴  (weak axis -> in PyNite bending about local z-axis = global y-axis!)
# It = 185.0 cm⁴   = 1.850e-6 m⁴  (torsional moment of inertia J)
A_heb300  = 1.491e-2
Iy_heb300 = 2.517e-4   # Bending about strong axis (curvature about local y-axis)
Iz_heb300 = 8.563e-5   # Bending about weak axis (curvature about local z-axis)
J_heb300  = 1.850e-6

model.add_section("HEB300", A_heb300, Iz_heb300, Iy_heb300, J_heb300)

# ==============================================================================
# 5. Create member (beam)
# ==============================================================================
# Note on local axes in PyNite:
# For a horizontal member along global X, local y points toward global +Y (up)
# and local z toward global +Z (out of plane). Bending in the x-y plane therefore
# occurs about the local z-axis (Iz in PyNite = Iy_heb300).
model.add_member("M1", "N1", "N2", "Stahl", "HEB300")

# ==============================================================================
# 6. Support conditions (2D simply supported beam in the x-y plane)
# ==============================================================================
# Parameter order: (node_name, support_DX, support_DY, support_DZ,
#                               support_RX, support_RY, support_RZ)
#
# Left (N1): Pinned/hinged support in plane (DX=True, DY=True, RZ=False)
#            + out-of-plane restraint (DZ=True, RX=True, RY=True)
model.def_support("N1", True, True, True, True, True, False)

# Right (N2): Roller support in plane (DX=False, DY=True, RZ=False)
#             + out-of-plane restraint (DZ=True, RX=True, RY=True)
model.def_support("N2", False, True, True, True, True, False)

# ==============================================================================
# 7. Example loading & load combination (for direct verification)
# ==============================================================================
# Uniformly distributed load q = -10.0 kN/m in global Y-direction (downward)
q = -10.0  # kN/m
model.add_member_dist_load("M1", "FY", q, q, 0.0, L, case="G")
model.add_load_combo("SLS", {"G": 1.0})

# ==============================================================================
# 8. Run analysis & print results
# ==============================================================================
model.analyze(check_statics=True)

# Analytical reference values for q = -10 kN/m, L = 8 m:
# Av = Bv = |q| * L / 2        = 40.00 kN
# M_max   = |q| * L² / 8       = 80.00 kNm
# w_max   = 5 * |q| * L⁴ / (384 * E * Iy) = 0.01007 m = 10.07 mm

print("=== SUPPORT REACTIONS (Load combination SLS) ===")
print(f"N1 (left) : FX = {model.nodes['N1'].RxnFX['SLS']:.2f} kN, "
      f"FY = {model.nodes['N1'].RxnFY['SLS']:.2f} kN")
print(f"N2 (right): FX = {model.nodes['N2'].RxnFX['SLS']:.2f} kN, "
      f"FY = {model.nodes['N2'].RxnFY['SLS']:.2f} kN")

print("\n=== INTERNAL FORCES & DEFLECTION ===")
m1 = model.members["M1"]
print(f"Max. bending moment Mz (midspan): {m1.max_moment('Mz', 'SLS'):.2f} kNm")
print(f"Min. bending moment Mz (midspan): {m1.min_moment('Mz', 'SLS'):.2f} kNm")
print(f"Max. shear force Fy             : {m1.max_shear('Fy', 'SLS'):.2f} kN")
print(f"Min. shear force Fy             : {m1.min_shear('Fy', 'SLS'):.2f} kN")
print(f"Max. deflection dy (midspan)    : {m1.min_deflection('dy', 'SLS') * 1000:.2f} mm")

# Optional: Plot internal force/deflection diagrams (requires matplotlib)
# m1.plot_moment("Mz", combo_name="SLS")
# m1.plot_shear("Fy", combo_name="SLS")
# m1.plot_deflection("dy", combo_name="SLS")
