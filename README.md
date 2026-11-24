<!-- AI helped creating the file -->
[//]: # (Author: Johannes Kalliauer, ChatGPT, Claude, Copilot)
[comment]: # (Created: 2026-11-20
Last Changes:
YYYY-MM-DD HH:mmCEST: Author:      Changes
2026-11-24 22:40 CET: Copilot:     Documented Undo toolbar action
2026-11-24 22:50 CET: Copilot:     Documented beam and support selection and editing
2026-11-24 23:05 CET: Copilot:     Documented node-on-beam splitting
2026-11-24 23:15 CET: Copilot:     Documented node context menu and script defaults
2026-11-24 23:24 CET: Copilot:     Documented canvas zoom and node deletion
2026-11-24 23:39 CET: Copilot:     Documented coordinated date-based versions
2026-11-24 23:47 CET: Copilot:     Documented timestamped model filename suggestion
2026-11-24 23:51 CET: Copilot:     Documented split confirmation button order
2026-11-24 23:53 CET: Copilot:     Separated GUI startup and usage instructions
2026-11-25 00:01 CET: Copilot:     Documented GUI help instructions menu
)

# MyFEM
Open-source 2D-Beam-Mechanics with simple GUI-Input for Linux-like-systems for making the structural analysis free accessible, transparent and easy reproducible.

## Aim and Scope
There exists a [German Scratchpad](https://github.com/JoKalliauer/MyFEM/blob/main/Developer_Scratchpad/Shedule_german.odt) for Developers

## Structure
```
                 MyFEM
                   |
          +--------+--------+
          |                 |
       GUI (Qt)         file-format
          |              JSON/YAML
          |                 |
          +--------+--------+
                   |
              FEM-Modell
                   |
          +--------+--------+
          |                 |
       PyNite            IQ100
          |                 |
          +--------+--------+
                   |
                Results
                   |
             GUI / Export
```

## Installation
Install the project dependencies from the repository root with:

```shell
uv sync
```


## Already implemented
 [x] first testfile
 [x] decission which GUI-Structure: PySide6
 [x] PyNite-Test-file: https://github.com/JoKalliauer/MyFEM/tree/main/test-files
 [x] JSON-Test-file:
 [x] plain-text-GUI-Protokoll for test-file
 [x] command-oriented GUI prototype

## Start the GUI

After `uv sync`, start the GUI from the repository root:

```shell
uv run myfem
```

Alternatively, use `run_myfem.bat` on Windows or `./run_myfem.sh` on Linux/WSL.

## Using the GUI

The toolbar provides **New**, **Open**, **Save**, **Undo**, **Node**, **Beam**,
**Support**, **Distributed load**, and **Calculate**. The Help menu contains
GUI instructions, version, and update information. Left-click **Node** or
**Beam** to enter it graphically; right-click to use its coordinate or endpoint
dialog. Press
**Esc** to return to Select mode. Scroll the mouse wheel to zoom the canvas.
Click a node, beam, or support to select it;
the selected object is highlighted. Double-click to edit it. Node coordinates,
beam endpoints and material/section references, and a support's 2D restraints
can be edited; support restraints outside the 2D plane are preserved. Changes
remain recorded in the `.mfs` script. On WSLg, Qt may require `libxcb-cursor0`.
When a node is added in the interior of a beam, MyFEM asks whether to split
that beam, with **Yes** before **No**. The split preserves its material,
section, and distributed loads, and finds unused child beam IDs. Right-click a
node to edit it, delete it, or edit its support (or add one if absent).
Deleting a node also removes connected beams, their loads, and any support at
the node.

On the first save of a new GUI model, the `.mfs` file receives version/date
comments and `model 2D xz x=right z=down` at the top. This metadata is not
added when saving an opened script. The save dialog suggests
`MyFEM-Model-YYYY-MM-DD_HH_mm.mfs`, using the local date and time.

## Model-entry defaults

The 2D X-Z model defaults node `y` to zero, so GUI-created node commands omit
`y=0`. Beams use the default material and section unless explicit names are
specified; the default options are omitted from GUI-created `.mfs` commands
and resolved when the JSON model is generated. Supports default `DY`, `RX`,
and `RZ` to true, so those values are omitted from GUI-created commands.
Distributed loads use `case=default`. A support with `DX`, `DZ`, and `RY` all
false is removed in 2D mode.

If a beam has no material or section definition, MyFEM uses these provisional
values:

| Default material | Value |
|---|---:|
| `E` | 210000000000 Pa |
| `G` | 80770000000 Pa |
| `nu` | 0.3 |
| `rho` | 78500 kg/m³ |

| Default section | Value |
|---|---:|
| `A` | 0.01491 m² |
| `I_yy` | 0.0002517 m⁴ |
| `I_zz` | 0.00008563 m⁴ |
| `I_T` | 0.00000185 m⁴ |

When exactly one differently named material or section exists, it is used for
`default`; if multiple exist without an explicit `default`, compilation fails.
Automatically inserted values are marked in JSON, and deformation results are
omitted for affected beams. If no combination is defined, `SLS default=1` is
generated only when loads use the `default` case; other load cases require an
explicit combination.

New JSON models use a string `format_version` with base `0.2` and a top-level
`beams` collection. The GUI/package version and format version share this base,
but their date suffixes can differ. The canonical date suffix supports year,
month, day, hour, and minute precision; new versions are limited to one per
minute. Package metadata uses equivalent PEP 440 dotted numeric components.
Existing numeric `format_version: 0.2` files remain supported; version `0.1` is
not supported.

## Result precision

By default, MyFEM writes `precision.absolute=0` and `precision.relative=1e-12`
to JSON. Values smaller than the greater of the absolute tolerance and the
relative tolerance times the largest result with the same unit are shown as
zero. The absolute tolerance uses internal SI values. Override either or both
settings in an `.mfs` script, for example:

```text
precision absolute=1e-11 relative=1e-12
```

Settings can also be given on separate `precision` lines.

## Reproducible model scripts

The simply supported beam example is defined by a replayable `.mfs` command
script. Compile it from the repository root with:

```shell
uv run python -m myfem.script tests/reference/simply_supported_beam/simply_supported_beam_heb300.mfs
```

By default, the JSON is written beside the script with the same base name.
An output path can be supplied as the second argument.

## Tests

Run the test suite with:

```shell
uv run pytest
```

## Generate a PyNite script and results log

From the folder containing `test.json`, run the MyFEM exporter using the
repository path on your computer:

```shell
uv run --project /path/to/MyFEM python /path/to/MyFEM/myfem/pynite_export.py ./test.json
```

This creates `test.py` next to the JSON file and writes PyNite's analysis
output to `test.out` next to the JSON file. The generated Python file is
standalone and can be run again with the same project environment:

```shell
uv run --project /path/to/MyFEM python ./test.py
```

Use `--python` and `--log` to choose different output paths.

# Declarations
## Vibe-Coding
Declare every file at the top the use of Artificial Intelligence (AI). This might be drop this later, however adding it later might be impossible.
Files without comments (e.g. *json) are excluded from this rule.
1) This file is created without AI
   * Everything is written by Hand out of the authors head, however AI might be used for finding a bug (not correcting) or recommendations of improvement.
   * The concept is designed by the Author, but might be unconsciously be influenced by past conversations with others or AI.
   * AI might be used for spell-checker, but all corrections are done by hand.
   * AI might be used by people with disabilities, to compensate the disability [e.g. screen-reader for blind people]
2) AI helped creating the file
   * the largest part (more than 50%) was created by human
   * AI might added comments, translated non-english-variables to english, improved the runtime, improved the structure
   * text might be copied directly from a LLM
3) AI created the file
   * at least some parts (maybe everything) was created by AI
  
## General
Author: Not everyone is familiar with Git, therefore explicitly mentioning at the beginning doesn't harm anyone<br/>
Create-Date:  for copyright and finding it in the history<br/>
Last-Changes: If something breaks, to find the important milestones.

# Safety and liability

MyFEM is a structural analysis tool. Results may be wrong, for example because of
software bugs, wrong input, unsuitable modelling assumptions or unsupported cases.
They must be independently checked by a qualified engineer before they are used
for any design, construction or safety-relevant decision. MyFEM does not replace
code (standard) checks such as Eurocode verifications.

The software is provided free of charge under the GPLv3. To the extent permitted
by applicable law, it comes without any warranty and the authors and copyright
holders are not liable for damages arising from its use (see sections 15 to 17 of
the [GPLv3](LICENSE)).

```
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. TO THE EXTENT PERMITTED BY APPLICABLE LAW,
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

# LICENSE
except written otherwise everything is published under GPLv3 https://github.com/JoKalliauer/MyFEM/blob/main/LICENSE<br/>
upon reasonable request other licenses might be possible (not for external sources)

## Exceptions from GPLv3:
Some are compatible with GPLv3, however I try to keep the original license wherever easily accessable
* everything in https://github.com/JoKalliauer/MyFEM/tree/main/not_GPLv3
  * [Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)](https://creativecommons.org/licenses/by-sa/3.0)
    * [Screenshot_von_RFEM.png](https://github.com/JoKalliauer/MyFEM/blob/main/not_GPLv3/CC-BY-SA3.0/Screenshot_von_RFEM.png), by @ndre@s on Wikimedia Commons; see the [attribution record](https://github.com/JoKalliauer/MyFEM/blob/main/not_GPLv3/CC-BY-SA3.0/Screenshot_von_RFEM.wiki).
  * [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/)
    * [RFEM-6-Scaled-Sums-Envelope.png](https://github.com/JoKalliauer/MyFEM/blob/main/not_GPLv3/CC-BY-SA4.0/RFEM-6-Scaled-Sums-Envelope.png), by @ndre@s on Wikimedia Commons; see the [attribution record](https://github.com/JoKalliauer/MyFEM/blob/main/not_GPLv3/CC-BY-SA4.0/RFEM-6-Scaled-Sums-Envelope.wiki).
    * The GUI toolbar icons in [not_GPLv3/CC-BY-SA4.0/RFEM-6-Scaled-Sums-Envelope](not_GPLv3/CC-BY-SA4.0/RFEM-6-Scaled-Sums-Envelope) are adapted from the image above.

## Acknowledgements

MyFEM is maintained and principally authored by [Johannes Kalliauer](https://github.com/JoKalliauer).

The solver is [PyNiteFEA](https://github.com/JWock82/Pynite), authored by
D. Craig Brinck, PE, SE, and maintained upstream by Craig ([`@JWock82`](https://github.com/JWock82)).
PyNiteFEA is distributed under the [MIT License](https://github.com/JWock82/Pynite/blob/main/LICENSE);
see its [contributors](https://github.com/JWock82/Pynite/graphs/contributors).
