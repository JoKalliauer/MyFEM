<!-- AI helped creating the file -->
<!-- Author: Johannes Kalliauer, Copilot -->
<!-- Created: 2026-11-22 -->
<!-- Last Changes:
YYYY-MM-DD HH:mm CET: Author: Changes
2026-11-22 19:55 CET: Copilot: Converted the ODT notes to Markdown without content edits
2026-11-22 19:58 CET: Copilot: Added current implementation status
-->

# Ziel von „MyFEM“:

## Aktueller Stand (2026-11-22)

- Das aktuelle Projektziel ist eine 2D-Stabwerksanalyse mit PyNite. Die ursprüngliche RatzFatz-Idee ohne definiertes Material und Querschnitt ist noch nicht umgesetzt; aktuelle Modelle benötigen beides.
- Vorhanden ist eine befehlsorientierte PySide6-GUI, kein grafischer 2D-Präprozessor. JSON ist das Modellformat; YAML gibt es nicht. `.mfs` unterstützt Material, Querschnitt, Knoten, Stab, Auflager, verteilte Stablasten und Lastkombinationen.
- **Calculate** speichert `.mfs`, erzeugt gleichnamige `.json`- und `.py`-Dateien, startet PyNite und speichert dessen Ergebnisausgabe in einer gleichnamigen `.out`-Datei. Änderungen im Editor sind erst nach Speichern oder Berechnen dauerhaft; eine Absturz-Wiederherstellung gibt es nicht.
- Modell und Dateien verwenden SI-Einheiten (m, N, Pa, kg, s, rad). Die aktuelle `.out`-Zusammenfassung enthält Auflagerkräfte FX/FZ, My- und Fz-Maxima/Minima sowie dz-Maximum (Ausgabe in kN, kNm und mm); keine Normalkraft und keine Diagramme.
- Noch nicht umgesetzt sind auswählbare Einheitensysteme, Punktlasten, Stabeinzellasten, Gelenke, geometrische Querschnittseingabe, Eigengewicht, Temperatur- und Auflagerverschiebungslasten sowie 3D.
- Der analytische Referenztest umfasst derzeit den einfach gelagerten Balken mit Gleichlast; weitere Referenzfälle fehlen.

## Ursprüngliche Idee

1. Ein einfaches Programm „RatzFatz“ mit GUI bei dem man eine Last eintippt, ein Momentenlinie bekommt, ohne dass man ein Querschnitt/Material definiert (EA=∞,GA=∞,EI=const). Zum schnellen Plausibiliseren, ob die Großenordnung von Berechnungsergebnissen passt.
1. Abspeichern der Eingaben in \*.dat, dass man in Sofistik-Teddy damit weiterarbeiten kann.

## Ziele: Nice-to-have but out-of-scope

1. Eigener Solver
1. Dateikonvertierung von Program X in Program Y (von opensouce-textbasierten), seperates Programm
1. Wählbare GUI, sodass jemand der RuckZuck, Sofistik, RFEM oder Abaqus sich zurechtfindet (Urheberrechte beachten), analog zu LibreOffice/Intellicad, die GUI soll die Namen „RatzFatz“ (sehr schnell), „Sofifem“ (sofia grichisch für Weisheit) und „QFEM“ (Quick-FEM) und „Rechenschieber“ (Deutsch für calculating aid) und soll als solche auch separat Downloadbar sein [wobei man die anderen nachladen kann]. Es geht hier nicht um implementierte Features, sondern nur die Anordnung der Buttons, so wie Libre-office mehrere Themes [Ribbons vs no-Ribbons] hat.
1. Einlesen von Sofistik-Teddy-Daten
1. IQ100 als analystischen Solver (nicht numerisch) implementieren [Inputdaten übergeben, solver laufen lassen, Ergebnisse betrachten]
1. Join ArcCraft (https://github.com/storytold https://getartcraft.com/) as FEM-Craft
1. Implementierung von Inca2 und ConDim
1. Einlesen von BIM.ifc-Modellen
1. Modellvereinfachungen
1. Erstellen eines Berichtes als bearbeitbares Office-Writer.odt
1. Parallelisierung des Solvers
1. Bemessungsmodule
1. Optimierung des Querschnittes (wie mit OptiSLang)

## Schritte für MyFEM

1. Lizenzen und Urheberrechte berücksichtigen
   1. GPLv3 wenn möglich
   1. externe Icons unter CC-BY-SA 4.0 oder CC-BY-SA 3.0 oder MIT
   1. eigene Icons wenn möglich Doppellizenz GPLv3 & CC-BY-SA 4.0
   1. solver PyNite unter MIT
1. basic GUI für PyNite für 2D-Stabwerke
   1. Einheiten: m,kN
   1. Präprozessor: Punkte, Auflager, Stäbe(ein konstanter linear elastischer Rechtecks-Querschnitt für alle), Gelenke
   1. Präprozessor: Punktlast, Stabeinzellast, Trapezlast für Stababschnitte (nur orthogonal oder parallel zur Stabachse) 
   1. Präprozessor: Löschen/Bearbeiten von Eingaben
   1. Präprozessor: Neue Datei, öffnen
   1. [x] PyNite-File schreiben und starten und Ergebnisse auslesen
   1. Postprozessor: Biegemoment, Querkraft, Normalkraft, Durchbiegung, Auflagerkräfte
   1. Progamm testen
   1. Einheiten Nutzer wählt zwischen:
      1. Einheitliches Einheitensystem Nutzerdefiniert wie in Abaqus
      1. beliebiges Einheitensystem das in Meter[m], bzw. [kg/s²] umgerechnet wird.
         1. Längen: mm,cm,m,km,in,ft,yd oder nl für Nutzerdefinierte Länge inkl. Umrechnung in m
         1. Kraft: N,kN oder nf für nutzerdefinierte Force inkl. Umrechnung in m
   1. Präprozessor: Eigengewicht, Stablasten (in globale Richtung, bezogen auf stablänge [Eigengewicht] vs orthongale Länge[Schnee]), Temperatur [Dehnungen/Stauchungen und Krümmungen], Auflagerverschiebung/drehung
   1. Präprozessor: Querschnitte: Rechteck, Rund, selbst definiert
   1. Icons
      1. Neue Datei, Öffnen, Rückgängig, Widerherstellen, Rechner [z.B.Qualculate!],Theorie I oder Theorie II Ordnung, Normalkraft anzeigen,Querkraft anzeigen,Moment anzeigen,Durchbiegung anzeigen,Auflagerkräfte anzeigen, Maus (aktuelle Auswahl beenden), Punkt erstellen, Stab zwischen bestehenden Punkten erstellen, Stab mit neuen Punkten erstellen, Momentengelenk an Knoten [alle Stäbe gelenkig], Momentengelenk an Stabende [nur der Stab hat ein Momentengelenk], Einzelkraft, Stabeinzellast, orthongale trapezlast, Last mit globalen Komponenten bezogen auf Stabachse, Trapezlast in globalen Komponenten bezogen auf ortogonal-länge, temperatur, Auflagerverschiebung, Pan, Zoom+-, Zoom Fenster, Zoom all
      1. Quellen: (hierarchisch geordnet)
         1. CC-BY-SA 4.0 https://commons.wikimedia.org/wiki/File:RFEM-6-Scaled-Sums-Envelope.png
         1. CC-BY-SA 3.0 https://commons.wikimedia.org/wiki/File:Screenshot_von_RFEM.png
         1. MIT  
            https://github.com/febiosoftware/FEBio
         1. neue svgs erstellen und als png einbinden (unter Doppellizenz CC-BY-SA 4.0 und GPLv3)
   1. Menüleiste:
      1. Datei: Öffnen, Speichern
      1. Optionen: Optionen
      1. ?: Lizenzinformationen
   1. Präprozessor: Modellbefehle werden in einem `.mfs`-Skript gesammelt, gespeichert und wieder eingelesen. Im Fall eines Absturzes ist der letzte ausgeführte Befehl mitgeschrieben und gespeichert.

## weitere Schritte mit Status „stalled“

1. weitere GUI für PyNite für 2D-Stabwerke
   1. GUI: Wenn das System instabil ist und min 1 Auflager im System ist, sieht man die kinematatische Kette.
   1. Präprozessor: Exzentrizitäten
   1. Präprozessor: Man kann optional auch Zoomeinstellungen mitprotokollieren, also man sieht wenn man einen Knoten hin und hinauszoomt
   1. Präprozessor: Man kann Rückgängig gemachte Optionen nicht mit ausgeben, so dass die fertige Struktur ohne nachträgliche Bearbeitungen gleich richtig erzeugt wird
1. Eigener Solver
1. IQ100 (TU-Wien) als analytischen Solver unterstützen
1. nachvollziehbare Querschnittsberechnung (in Tabellenkalkulation.ods, die von MyFEM geschrieben werden kann)
1. Stabsysteme in 3D in MyFEM implementieren
1. Flächensysteme in MyFEM implementieren
1. Funktionen von ConDIM und Inka implementieren
1. Volums-elemente in MyFEM implementieren
1. eingeschränkte Kompatibilät mit anderen GUIs/Solvern

# Iconleiste

Zweizeilige Icon-Leiste.
1 Zeile: Präpozessor
  a. neue Datei (*.mfs und *.json)
  b. öffnen (*.mfs)
  c. speichern (*.mfs und *.json)
  d Markiertes Element löschen (mitdokumentieren in *.mfs)
  e. Rückgänig (mitdokumentieren in *.mfs)
  f. Wiederherstellen
  g Rechner starten (wenn installiert in dieser Reihenfolge: "Qalculate!" "gnome-calculator" "KCalc" "galculator" "xfe4-calc" "calc.exe", wenn keiner dann ausgegraut)
  h Theorie I-Ordnung (vorausgewählt bei Neuer Datei)
  i Theorie II-Ordnung
  j Material & Querschnitt
  k Mauszeiger zum anklicken (vorausgewählt beim öffnen/erstellen einer Datei)
  l. neuer Knoten erstellen
  m. Auflagerbedigungen an Knoten
  n Stab zwischen bestehenden Knoten
  o. Stab samt Anfangs- und End-Knoten erstellen
  p Knoten zu einem Vollgelenk (Biegemoment) machen
  q Stabende mit einem Gelenk (Biegemoment) ergänzen [nur sinnvoll ab 3 Stäbe die an dem Knoten anschließen]
  r. Einzellast an Knoten
  s Einzellast an Stab
  t. Trapezlast orthongal zum Stab
  u Zoom +/-
  v Zoom Fenster
  w Zoom Grenzen und Zentrieren
  x. Berechnen (*.mfs => *.json => *.py => Pynite => *.out)
2. Zeile Postprocessor
  A Normalkraft anzeigen
  B Querkraft anzeigen
  C Biegemoment anzeigen
  D Durchbiegung anzeigen
  
  
