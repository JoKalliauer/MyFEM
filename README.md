<!-- AI helped creating the file -->
[//]: # (Author: Johannes Kalliauer, ChatGPT, Claude)
[comment]: # (Created: 2026-11-20
Last Changes:
YYYY-MM-DD HH:mmCEST: Author:      Changes
2026-11-21 13:53 CET: J.Kalliauer: License, Declarations
2026-11-22 10:40 CET: J.Kalliauer: Aim more precise
2026-11-22 10:56 CET: ChatGPT:     Structure
2026-11-22 13:06 CET: Claude:      Safety and liability
2026-11-22 14:04 CET: J.Kalliauer: already implemented
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
Currently there is no finished draft to run, you could help developing instead.
### Prerequisites
* PyNite


## Already implemented
 [x] first testfile
 [x] decission which GUI-Structure: PySide6
 [x] PyNite-Test-file: https://github.com/JoKalliauer/MyFEM/tree/main/test-files
 [ ] JSON-Test-file:
 [ ] plain-text-GUI-Protokoll for test-file
 [ ] GUI

# Declarations
## Vibe-Coding
Declare every file at the top the use of Artificial Intelligence (AI). This might be drop this later, however adding it later might be impossible.
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
