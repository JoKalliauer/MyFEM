#AI created the file 
#Author: Gemini, Johannes Kalliauer
#Copyright,License: GPLv3
#Create-Date: 2026-11-21

#Last changes:
#2026-11-21 14:16 "PyNite" to "Pynite"

from Pynite import FEModel3D

# ==============================================================================
# 1. Modell initialisieren (Einheitensystem: kN, m)
# ==============================================================================
model = FEModel3D()

# Spannweite [m]
L = 8.0

# ==============================================================================
# 2. Knoten definieren
# ==============================================================================
# N1: Auflager links (x = 0)
# N2: Auflager rechts (x = 8.0 m)
model.add_node("N1", 0.0, 0.0, 0.0)
model.add_node("N2", L, 0.0, 0.0)

# ==============================================================================
# 3. Material definieren: Baustahl S235 / S355 (EN 1993-1-1)
# ==============================================================================
E = 210e6      # Elastizitätsmodul: 210.000 N/mm² = 210e6 kN/m²
G = 80.77e6    # Schubmodul:         80.770 N/mm² = 80.77e6 kN/m²
nu = 0.3       # Querdehnzahl [-]
rho = 78.5     # Wichte [kN/m³]

model.add_material("Stahl", E, G, nu, rho)

# ==============================================================================
# 4. Querschnitt definieren: HEB 300 (EN 10365 / DIN 1025-2)
# ==============================================================================
# Normwerte HEB 300 (h = 300 mm, b = 300 mm, tw = 11 mm, tf = 19 mm, r = 27 mm):
# A  = 149,1 cm²   = 1.491e-2 m²
# Iy = 25170 cm⁴   = 2.517e-4 m⁴  (starke Achse -> in PyNite lokale z-Achse!)
# Iz = 8563 cm⁴    = 8.563e-5 m⁴  (schwache Achse -> in PyNite lokale y-Achse!)
# It = 185,0 cm⁴   = 1.850e-6 m⁴  (Torsionsträgheitsmoment J)
A_heb300  = 1.491e-2
Iy_heb300 = 2.517e-4   # Biegung um starke Achse
Iz_heb300 = 8.563e-5   # Biegung um schwache Achse
J_heb300  = 1.850e-6

model.add_section("HEB300", A_heb300, Iz_heb300, Iy_heb300, J_heb300)

# ==============================================================================
# 5. Stab (Träger) erzeugen
# ==============================================================================
# Hinweis zu lokalen Achsen in PyNite:
# Bei horizontalem Stab entlang global X zeigt lokal y nach global +Y (oben)
# und lokal z nach global +Z (aus der Ebene). Biegung in der x-y-Ebene erfolgt
# daher um die lokale z-Achse (Iz in PyNite = Iy_heb300).
model.add_member("M1", "N1", "N2", "Stahl", "HEB300")

# ==============================================================================
# 6. Auflagerbedingungen (2D-Einfeldträger in der x-y-Ebene)
# ==============================================================================
# Parameter-Reihenfolge: (node_name, support_DX, support_DY, support_DZ,
#                                    support_RX, support_RY, support_RZ)
#
# Links (N1): Festlager in der Ebene (DX=True, DY=True, RZ=False)
#             + Festhaltung aus der Ebene (DZ=True, RX=True, RY=True)
model.def_support("N1", True, True, True, True, True, False)

# Rechts (N2): Loslager in der Ebene (DX=False, DY=True, RZ=False)
#              + Festhaltung aus der Ebene (DZ=True, RX=True, RY=True)
model.def_support("N2", False, True, True, True, True, False)

# ==============================================================================
# 7. Beispiel-Belastung & Lastkombination (zur direkten Prüfung)
# ==============================================================================
# Gleichstreckenlast q = -10.0 kN/m in globaler Y-Richtung (nach unten)
q = -10.0  # kN/m
model.add_member_dist_load("M1", "FY", q, q, 0.0, L, case="G")
model.add_load_combo("SLS", {"G": 1.0})

# ==============================================================================
# 8. Berechnung ausführen & Ergebnisse ausgeben
# ==============================================================================
model.analyze(check_statics=True)

# Analytische Vergleichswerte für q = -10 kN/m, L = 8 m:
# Av = Bv = |q| * L / 2        = 40.00 kN
# M_max   = |q| * L² / 8       = 80.00 kNm
# w_max   = 5 * |q| * L⁴ / (384 * E * Iy) = 0.01007 m = 10.07 mm

print("=== AUFLAGERKRÄFTE (Lastkombination SLS) ===")
print(f"N1 (links) : FX = {model.nodes['N1'].RxnFX['SLS']:.2f} kN, "
      f"FY = {model.nodes['N1'].RxnFY['SLS']:.2f} kN")
print(f"N2 (rechts): FX = {model.nodes['N2'].RxnFX['SLS']:.2f} kN, "
      f"FY = {model.nodes['N2'].RxnFY['SLS']:.2f} kN")

print("\n=== SCHNITTGRÖSSEN & DURCHBIEGUNG ===")
m1 = model.members["M1"]
print(f"Max. Biegemoment Mz (Feldmitte): {m1.max_moment('Mz', 'SLS'):.2f} kNm")
print(f"Min. Biegemoment Mz (Feldmitte): {m1.min_moment('Mz', 'SLS'):.2f} kNm")
print(f"Max. Querkraft Fy              : {m1.max_shear('Fy', 'SLS'):.2f} kN")
print(f"Min. Querkraft Fy              : {m1.min_shear('Fy', 'SLS'):.2f} kN")
print(f"Max. Durchbiegung dy (Feldmitte): {m1.min_deflection('dy', 'SLS') * 1000:.2f} mm")

# Optional: Schnittgrößenverlauf plotten (benötigt matplotlib)
# m1.plot_moment("Mz", combo_name="SLS")
# m1.plot_shear("Fy", combo_name="SLS")
# m1.plot_deflection("dy", combo_name="SLS")
