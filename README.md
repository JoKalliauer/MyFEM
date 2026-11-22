<!-- AI helped creating the file -->
[//]: # (Author: Johannes Kalliauer, ChatGPT, Claude, Copilot)
[comment]: # (Created: 2026-11-20
Last Changes:
YYYY-MM-DD HH:mmCEST: Author:      Changes
2026-11-21 13:53 CET: J.Kalliauer: License, Declarations
2026-11-22 10:40 CET: J.Kalliauer: Aim more precise
2026-11-22 10:56 CET: ChatGPT:     Structure
2026-11-22 13:06 CET: Claude:      Safety and liability
2026-11-22 14:04 CET: J.Kalliauer: already implemented
2026-11-22 14:31 CET: J.Kalliauer: json without coding-declations
2026-11-22 18:40 CET: Copilot:     Documented replayable model command scripts
2026-11-22 18:48 CET: Copilot:     Documented command editor GUI
2026-11-22 18:50 CET: Copilot:     Documented dependency setup and tests
2026-11-22 19:28 CET: Copilot:     Documented PyNite script and result-log generation
2026-11-22 19:40 CET: Copilot:     Documented GUI calculation and .out results
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

## Run the GUI

Start the command-oriented GUI from the repository root with:

```shell
uv run python -m myfem.gui
```

Commands entered in the window are validated and appended to the script editor.
Save them as `.mfs`, then use **Calculate** to generate the matching `.json` and
`.py`, run PyNite, and save the results in the matching `.out` file.
The GUI is an initial command editor; the planned 2D graphical model editor is
not implemented yet. On WSLg, Qt may require `libxcb-cursor0`.

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
    * [Screenshot_von_RFEM.png](https://github.com/JoKalliauer/MyFEM/blob/main/not_GPLv3/CC-BY-SA3.0/Screenshot_von_RFEM.png) see [not_GPLv3/CC-BY-SA3.0/Screenshot_von_RFEM.wiki](https://github.com/JoKalliauer/MyFEM/blob/main/not_GPLv3/CC-BY-SA3.0/Screenshot_von_RFEM.wiki)
  * [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/)
    * [RFEM-6-Scaled-Sums-Envelope.png ](https://github.com/JoKalliauer/MyFEM/blob/main/not_GPLv3/CC-BY-SA4.0/RFEM-6-Scaled-Sums-Envelope.png) see [not_GPLv3/CC-BY-SA4.0/RFEM-6-Scaled-Sums-Envelope.wiki](https://github.com/JoKalliauer/MyFEM/blob/main/not_GPLv3/CC-BY-SA4.0/RFEM-6-Scaled-Sums-Envelope.wiki)
