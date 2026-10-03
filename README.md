# Wada Primary

A Quarto reveal.js theme for academic talks, named for Sanzo Wada: its four primary colors come from his *Dictionary of Color Combinations*, and its extended palette from the combinations they appear in. It provides:
- white 16:9 slides and Inter type
- a navy, green, rust and orange palette
- layouts for the usual parts of a research presentation: outline, research questions, study design, policy timeline, figures, regression tables, key numbers and findings

## Quick start

You need [Quarto](https://quarto.org) 1.5 or later.

1. Copy this folder and rename `template.qmd` for your talk.
2. Render it with `quarto render template.qmd`, or with the Render button in RStudio or Positron.
3. Replace the sample slides with your own. Each slide in `template.qmd` shows one layout.

To use the theme in an existing project, copy `_extensions/wada-primary/` next to your `.qmd` file and set:

```yaml
format:
  wada-primary-revealjs:
    footer: "Short presentation title"
```

If this folder is published as a GitHub repository, others can start a new talk from it with `quarto use template <user>/<repo>`.

## Exporting to PDF

Each slide prints on its own 16:9 page, with its slide number and footer. The title slide has neither.

**With the script.** This needs Chrome, Chromium or Edge; nothing else to install.

```bash
python3 _extensions/wada-primary/export_pdf.py template.html
```

**From the browser:**
1. Open the rendered deck in Chrome and press **E**, or add `?print-pdf` to the URL.
2. Print and choose **Save as PDF**.
3. Set **Margins** to *None* and keep **Background graphics** on.

## Folder contents

| Path | What it is |
|---|---|
| `template.qmd` | Example deck with every layout; start here |
| `LICENSE` | MIT license |
| `images/` | Example figures (replace with your own) |
| `_extensions/wada-primary/wada-primary.scss` | Styles: palette, type, layouts |
| `_extensions/wada-primary/wada-primary.lua` | Slide backgrounds, section numbering, timeline layout |
| `_extensions/wada-primary/wada-primary.html` | Zero-padded slide numbers; footers and numbers on PDF pages |
| `_extensions/wada-primary/palette.csv` | The categorical palette, for matching figure colors |
| `_extensions/wada-primary/wada_palette.py` | Regenerates palette colors 5 and up (see below) |
| `_extensions/wada-primary/export_pdf.py` | One-command PDF export |

## Slides

| Markdown | Layout |
|---|---|
| `## Title {.cover}` | Title slide, with `::: subtitle`, `::: venue` (top label) and `::: byline` (authors, affiliation) |
| `# Section` | Section slide, numbered automatically (01, 02, …) |
| `## Outline {.agenda}` | Numbered contents rows. The list items are `1. Name [description]{.desc}` |
| `## Title {.statement}` | Numbered research questions in larger type, plus an optional `::: note` |
| `## Title {.figure-right}` | Text on the left. The figure goes in `::: figure-panel` on the right |
| `## Key finding 1 {.takeaway}` | One finding stated in a sentence beside a rule, then a supporting line |
| `## Thank you {.closing}` | Closing slide, with `::: byline` |
| `.bg-navy`, `.bg-rust`, `.bg-green`, `.bg-orange` | Background color for any slide |

A slide whose only content is an image (plus an optional caption) stretches the image to fill the space below the title.

## Blocks

| Markdown | Use |
|---|---|
| `::: cols` holding `::: col` blocks | Columns with a colored rule above each. Add `.bottom` to pin them to the bottom of the slide |
| `::: steps` holding `::: col` blocks | Numbered columns, e.g. for study design steps |
| `::: stats` holding `::: col` blocks | Key numbers, written as `[20.6M]{.num}` followed by `[label]{.label}` |
| `::: {.gantt start=2016 end=2023 res=2}` | A timeline. Bars are `[Label [detail]{.sub}]{from=2020.5 to=2022}`. `to` defaults to `end`, and `res=2` allows half-year starts |
| `::: ruled` | A block with a rule above it, a small `###` heading and compact text |
| `::: {.callout-note title="…"}` | Quarto callout, styled as a tinted box |
| `::: aside` | Source note at the bottom of the slide |
| `::: references` | Hanging-indent reference list. Citations from `bibliography:` are styled the same way |
| `::: notes` | Speaker notes (press **S** while presenting) |

Inline: `[text]{.hl}` (highlight, also works in table cells), `[text]{.eyebrow}` (small caps label), `.lead`, `.small`, `.muted`, `.accent`. Add `{.paper}` to an image for a hairline frame.

## Palette

Steps, columns, key numbers, outline rows and timeline bars take one color per item, in this order:

| # | Color | Hex | Source |
|---|---|---|---|
| 1 | Navy | `#202d85` | Theme |
| 2 | Green | `#58771e` | Theme |
| 3 | Rust | `#a93400` | Theme |
| 4 | Orange | `#ff8c00` | Theme (lines and fills only; numbers use dark text) |
| 5 | Artemesia Green | `#65a98f` | Wada combination 312 |
| 6 | Blue | `#0d75ff` | Wada 267, 333 |
| 7 | Eosine Pink | `#ff5ec4` | Wada 108, 242 |
| 8 | Antwarp Blue | `#008aa1` | Wada 140 |

The four theme colors are themselves colors from Sanzo Wada's *A Dictionary of Color Combinations*: Violet Blue, Olive Green, Burnt Sienna and Yellow Orange.

`wada_palette.py` produces colors 5 and up. It:
1. Reads the dictionary from <https://sanzo-wada.dmbk.io/>.
2. Finds the combinations that contain the theme colors.
3. Keeps the companion colors that appear with them most often and are distinct and visible on white.

```bash
python3 _extensions/wada-primary/wada_palette.py --extra 4   # number of colors after the first four
```

The script updates `wada-primary.scss` and `palette.csv`. Use the CSV to make figures match the slides:

```r
pal <- read.csv("_extensions/wada-primary/palette.csv")
ggplot(df, aes(year, rate, color = group)) + geom_line() +
  scale_color_manual(values = pal$hex)
```

```python
import pandas as pd
colors = pd.read_csv("_extensions/wada-primary/palette.csv")["hex"].tolist()
```

In the CSV:
- `hex` is the line or fill color.
- `text_hex` is a version dark enough for text on white.
- `label_on_fill` is the label color to use on that fill.

## Customizing

**Slide backgrounds** come from document metadata:

```yaml
wada-primary:
  cover-bg: "#202d85"     # "none" for a white title slide
  divider-bg: "#202d85"   # section slides
  closing-bg: "#202d85"   # defaults to divider-bg
  finding-bg: none        # key-finding slides
```

**Transitions** are off by default. For the whole deck, add `transition: fade` (or `slide`) under `wada-primary-revealjs`. For one slide, add the attribute to its heading: `## Title {data-transition="fade"}`.

**Style variables.** Put a small SCSS file after the theme, and set any of the variables below in its `/*-- scss:defaults --*/` section:

```yaml
format:
  wada-primary-revealjs:
    theme: [_extensions/wada-primary/wada-primary.scss, custom.scss]
```

| Variable | Sets |
|---|---|
| `$primary`, `$accent`, `$emphasis`, `$heading-color` | Main color roles |
| `$categorical` | Turns the one-color-per-item palette on or off (default `true`) |
| `$header-style` | Slide titles: `plain` (default), `rule` or `banner` (a band behind the title) |
| `$divider-style` | Section slides: `filled` (default) or `progress` (white, with a progress line) |
| `$kicker` | Shows the section name above each slide title |
| `$section-coding` | Colors each section from `$section-colors`. Pair it with `section-colors` metadata |
| `$stripe` | Adds a four-color bar along the top of every slide |
| `$small-text` | Size of references, slide number and footer (default `0.62`) |
| `$font-family-sans-serif` | The font for headings and text |

The canvas is 1600 × 900. Layouts are positioned for that size, so leave `width`, `height` and `margin` at their defaults.

## Notes

- **Fonts:** Inter loads from Google Fonts. To present offline, render with `embed-resources: true` or install Inter locally.
- **Narrow screens:** on phones (under 435px wide), reveal.js shows the deck as a scrolling page. That is expected.
- **Palette edits:** if you change the theme colors, keep the hex values in `wada-primary.scss`, `wada-primary.lua` and `wada_palette.py` in sync.

## AI disclosure

This theme was built with Claude (Opus 5.5), Anthropic's AI assistant, under the author's direction. That covers the stylesheet, the Lua filter, the scripts, the example figures and this documentation. The example figures use made-up data. Check rendered slides and exported PDFs before you present or share them.

## License

[MIT](LICENSE). The license covers the theme, the template and the scripts.

Inter is licensed separately, under the SIL Open Font License. It is loaded from Google Fonts and is not included in this folder.

## Credits

- **Colors:** combinations from Sanzo Wada, *A Dictionary of Color Combinations*, as published at <https://sanzo-wada.dmbk.io/>.
- **Font:** [Inter](https://rsms.me/inter/) by Rasmus Andersson, SIL Open Font License.
- **Software:** built on [Quarto](https://quarto.org) and [reveal.js](https://revealjs.com).
