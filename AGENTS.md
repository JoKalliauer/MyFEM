<!-- AI created the file -->
[//]: # (Author: claude.ai, Johannes Kalliauer)
[comment]: # (Created: 2026-11-22
Last Changes:
YYYY-MM-DD HH:mmCEST: Author:      Changes
2026-11-22 12:32 CET: Claude:      Initial draft
2026-11-22 12:49 CET: J.Kalliauer: litte corrections
)

# AGENTS.md: Instructions for AI coding assistants

This file is read at the start of every session. Follow it unless the human maintainer explicitly overrides it in the current conversation. If a rule here conflicts with a request, say so and ask before proceeding.

## 1. Project summary

MyFEM is open-source structural beam analysis (2D now, 3D planned) with a desktop GUI, intended to make structural analysis freely accessible, transparent and easy to reproduce. Solvers: PyNiteFEA first, IQ100 later.

Target platforms: **Linux, Windows (native) and WSL (WSLg).** Everything must work on all three. Mac might be a future plan, but should not be officially be tested against.

## 2. Language

* All code, identifiers, comments, docstrings, commit messages, issue text and documentation are written in **English**.
* Do not introduce German identifiers. If you find some, translate them (and mention it in the file's change log).

## 3. Tech stack (decided)

| Task | Library |
|---|---|
| GUI | PySide6 (Qt Widgets) |
| 2D editor | `QGraphicsView` / `QGraphicsScene` |
| 3D view (later) | PyVista + pyvistaqt |
| Plots (N/V/M etc.) | Matplotlib (`FigureCanvasQTAgg`); drawing diagrams in the scene may follow later |
| FEM solver | PyNiteFEA (IQ100 later) |
| Model files | JSON |
| Configuration | see section 9 |
| Tables | Qt Model/View |
| Undo/redo | `QUndoStack` / `QUndoCommand` |
| Tests | pytest |
| Lint/format | ruff |
| Environment | uv (`pyproject.toml` + `uv.lock`) |
| Deployment (later) | `pyside6-deploy` |

Do **not** add other GUI toolkits (PyQt, wxPython, Tk, GTK, Dear PyGui, Electron/Tauri, browser/web frontends, Streamlit/Gradio/Kivy). Do not add new dependencies without asking; justify any proposal in one sentence.

## 4. Portability rules

* Use `pathlib.Path` for all paths. Never build paths with string concatenation or hard-coded separators.
* No shell-specific calls (`os.system`, `subprocess` with `bash`, `source`, `~` expansion by shell). If a subprocess is unavoidable, pass an argument list, never `shell=True`.
* Read and write text files with an explicit `encoding="utf-8"`.
* Use `uv sync` and `uv run ...` in all documentation. Do not tell users to activate a venv.
* Do not rely on case-sensitive file names or on Linux-only behavior.
* Qt on WSLg may need `libxcb-cursor0`; mention this in the docs, do not work around it in code.

## 5. Architecture

```
GUI (PySide6)  ->  commands (QUndoCommand)  ->  Model (pure Python)  ->  Solver wrapper  ->  Results
```

1. **The model and solver layers never import Qt.** (`myfem/model`, `myfem/solver`, `myfem/io`). They must be testable with plain pytest and no display.
2. A thin **Qt adapter layer** wraps the pure-Python model (Qt item models, change signals).
3. **All model changes go through `QUndoCommand` subclasses** (`AddNode`, `MoveNode`, `AddMember`, `DeleteMember`, ...). Views and tools must never mutate the model directly. This guarantees consistent undo/redo and keeps 2D and 3D views in sync.
4. Views react to model-change signals and redraw. Views do not talk to each other.
5. **Tools** (select, node, member, ...) are small state machines separate from the view widgets. "Member from node A to node B" uses the same tool logic in 2D and 3D; only the source of click events differs.
6. The solver wrapper is the only place that knows PyNite's API and its axis conventions (see section 7).

Suggested layout:

```
myfem/
  model/      # dataclasses, validation, no Qt
  io/         # JSON load/save, schema, version migration
  solver/     # PyNite wrapper (later IQ100), unit/axis conversion
  gui/        # PySide6 only: adapters, commands, tools, views, dialogs
  cli.py      # headless run: load JSON, solve, print/plot
tests/
  reference/  # reference cases with known analytical solutions
examples/
```

## 6. Interaction concept

| | 2D | 3D |
|---|---|---|
| Create node | click in the canvas (grid snapping) | type coordinates in the node table or a dialog |
| Move node | drag | edit coordinates in the table |
| Create member | click or drag from node to node | click node A, then node B (picking) |
| Selection | click, rubber band | click a node or member (picking) |
| Technology | QGraphicsView | PyVista (pyvistaqt) |

* The 2D editor is built first. The 3D view starts **read-only** (model, deformation, internal forces); 3D picking for members comes after that.
* The node table is the shared coordinate input for 2D and 3D.
* 3D means picking existing objects only, never free positioning in space.

## 7. Units, axes, conventions

* **All internal data and all files use SI units**: meter (m), newton (N), pascal (Pa), kilogram (kg), second (s), radian (rad).
* The model file contains a `"units": "SI"` field so future unit systems can be distinguished.
* **The data model is 3D from the start**: nodes have `x, y, z` (2D models use `y = 0` and `"dimension": 2`), cross sections have `A, Iyy, Izz, I_T`, supports have six degrees of freedom, loads are vectors, members have a cross-section orientation (roll angle or reference vector).
* Global coordinate system: **Z down** (structural convention), right-handed. PyNite uses Y up; the conversion lives only in the solver wrapper and must be covered by tests.
* Document the sign conventions (axial force, shear, moment, rotation direction, local member axes) in `docs/conventions.md` and keep it in sync with the code. Never change a sign convention silently.
* Default local axis rule for members: derived from member direction and global Z; document the special case of vertical members.

## 8. Model file format

* JSON, UTF-8, one top-level object with `"format_version"`, `"units"`, `"dimension"`, `"materials"`, `"sections"`, `"nodes"`, `"members"`, `"supports"`, `"loads"`.
* Every format change bumps `format_version` and adds a migration; old files after the initial release of 0.1 must keep loading.
* Validate on load (JSON Schema or explicit checks) and fail with clear, specific error messages.
* Use stable string IDs for nodes and members, not list indices.
* Write deterministic output (sorted keys, fixed indentation) so files diff cleanly in Git.

## 9. Configuration

Configuration (user preferences, not model data) uses **TOML** read with `tomllib` from the standard library, unless the maintainer decides on YAML. Do not add a YAML dependency without asking. Model data is never stored in the config file.

## 10. Testing and verification

* Write pytest tests for model, io and solver **before** building GUI features on top of them.
* Reference cases with known analytical solutions (for GA=\infty, EA=\infty, and geometric linear and material linear), e.g.:
  * simply supported beam with uniform load q, span L: `M_max = q*L^2/8`, `delta_max = 5*q*L^4/(384*E*I)`
  * cantilever with end load P: `M_max = P*L`, `delta = P*L^3/(3*E*I)`
  * two-span continuous beam
  * a spatial frame with torsion (once 3D is implemented)
* Do not "fix" a failing reference test by changing the expected value without explaining the analytical reason.
* GUI tests: keep them few and use `pytest-qt` with the offscreen platform (`QT_QPA_PLATFORM=offscreen`, set from Python/conftest, not from the shell).
* Before finishing a task run: `uv run ruff check`, `uv run ruff format`, `uv run pytest`.

## 11. Working style

* Work in **small vertical slices**; one logical change per commit, tests green before the next step. Suggested order:
  1. JSON load, solve with PyNite, print results (tested against reference cases)
  2. Matplotlib output for N/V/M
  3. Empty PySide6 window with a QGraphicsView
  4. Create/move nodes in 2D
  5. Members, then supports and loads
  6. Tables and undo/redo
  7. 3D view (read-only), then 3D member picking
* Do not refactor unrelated code. Do not rename or move files without being asked.
* Prefer simple, readable code with type hints. Keep functions short, docstrings for public API.
* If a requirement is ambiguous (sign convention, unit, behavior), ask instead of guessing.
* Never invent PyNite API. If unsure, check the installed version's source or documentation.

## 12. Declaration rules (AI usage, from README)

Every file declares AI usage at the top:

1. `This file is created without AI`
2. `AI helped creating the file` (more than 50% by a human; AI may add comments, translate, improve structure or runtime)
3. `AI created the file` (at least some parts, maybe everything, by AI)

Every file also gets an author line, a creation date and a change log in the header (see the README: `Author`, `Created`, `Last Changes` with `YYYY-MM-DD HH:mm CET: Author: Changes`).

* When you create a file, add the header with the correct category (normally category 3 unless a human wrote most of it).
* When you edit a file, add a change log line with your name as author, and **upgrade the category** if your share makes the old one untrue.
* Files that cannot hold comments (e.g. JSON) are declared in a neighboring file or in the README.

## 13. Safety and liability

This is structural engineering software. Results must be independently verified by a qualified person. Do not weaken validation or hide warnings to make a calculation "succeed". Keep the "no warranty, results must be checked" notice in the README. Report solver warnings (unstable structure, singular matrix) clearly to the user.

## 14. License

Default license is GPLv3 (the license may still change; do not hard-code license assumptions in code). Respect the exceptions documented in the README for files under `not_GPLv3/`. Do not copy code from other projects without checking license compatibility and recording the source.
