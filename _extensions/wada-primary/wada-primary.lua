-- wada-primary.lua: layout helpers for the Wada Primary reveal.js theme.
--
--   * Slide classes set the slide background: .cover/.divider/.closing use the
--     colors from document metadata (below); .bg-navy/.bg-rust/.bg-orange/
--     .bg-green/.bg-white set one directly.
--   * Level-1 headings (# Section) become divider slides.
--   * ::: {.gantt start=2016 end=2023} lays out bars given from= / to= years.
--
-- Metadata (all optional; "none" leaves the slide white):
--   wada-primary:
--     cover-bg: "#202d85"
--     divider-bg: "#202d85"
--     closing-bg: "#202d85"   # defaults to divider-bg
--     finding-bg: none        # key-finding (.takeaway) slides
--     section-colors: ["#202d85", "#58771e", "#a93400"]   # cycles over dividers
--
-- Every slide also gets a sec-N class and a data-section attribute naming the
-- current section, which the stylesheet can use for section colors and kickers.

-- Keep in sync with the palette in wada-primary.scss
local palette = {
  navy = "#202d85",
  rust = "#a93400",
  orange = "#ff8c00",
  green = "#58771e",
  white = "#ffffff",
}

local options = {
  cover = palette.navy,
  divider = palette.navy,
  closing = nil, -- falls back to divider
  finding = nil,
  section_colors = nil,
}

local no_stretch_containers = { "cols", "steps", "stats", "gantt", "agenda", "figure-panel" }

local function has_any(classes, list)
  for _, c in ipairs(list) do
    if classes:includes(c) then return true end
  end
  return false
end

local function add_class(classes, name)
  if not classes:includes(name) then classes:insert(name) end
end

local function prepend_style(attributes, style)
  attributes.style = style .. (attributes.style or "")
end

-- Options -------------------------------------------------------------------

local function read_options(meta)
  local opts = meta["wada-primary"]
  if type(opts) ~= "table" then return nil end
  local function get(key)
    if opts[key] == nil then return nil end
    return pandoc.utils.stringify(opts[key])
  end
  options.cover = get("cover-bg") or options.cover
  options.divider = get("divider-bg") or options.divider
  options.closing = get("closing-bg") or options.closing
  options.finding = get("finding-bg") or options.finding
  local colors = opts["section-colors"]
  if type(colors) == "table" and #colors > 0 then
    options.section_colors = {}
    for _, c in ipairs(colors) do table.insert(options.section_colors, pandoc.utils.stringify(c)) end
  end
end

local function slide_color(value)
  if value == nil or value == "" or value == "none" then return nil end
  return palette[value] or value
end

-- Slides --------------------------------------------------------------------

local section_index = 0
local section_name = nil

local function Header(el)
  if el.level > 2 then return nil end

  if el.level == 1 then
    section_index = section_index + 1
    section_name = pandoc.utils.stringify(el.content)
  end
  if section_index > 0 then
    add_class(el.classes, "sec-" .. section_index)
    if el.level == 2 and section_name ~= "" then
      el.attributes["data-section"] = section_name
    end
  end

  local bg
  for name, hex in pairs(palette) do
    if el.classes:includes("bg-" .. name) then bg = hex end
  end
  local role = (el.classes:includes("cover") and "cover")
    or (el.classes:includes("closing") and "closing")
    or (el.classes:includes("divider") and "divider")
    or (el.classes:includes("dark") and "dark")
  if el.level == 1 and not bg and not role then
    add_class(el.classes, "divider")
    role = "divider"
  end

  if not (el.attributes["background-color"] or el.attributes["data-background-color"]) then
    if not bg then
      local sc = options.section_colors
      if role == "cover" then bg = slide_color(options.cover)
      elseif role == "divider" and sc then bg = slide_color(sc[(section_index - 1) % #sc + 1])
      elseif role == "divider" then bg = slide_color(options.divider)
      elseif role == "closing" then bg = slide_color(options.closing or options.divider)
      elseif role == "dark" then bg = palette.navy
      elseif el.classes:includes("takeaway") then bg = slide_color(options.finding)
      end
    end
    if bg then el.attributes["background-color"] = bg end
  end

  -- Lets the stylesheet hide the slide number and footer on the cover
  if role == "cover" then
    el.attributes["data-state"] = "is-cover"
  end
  return el
end

-- Components ----------------------------------------------------------------

-- Timeline: <div class="gantt" start="2016" end="2023" res="2">.
-- `res` subdivides each year (2 = half years, 4 = quarters, 12 = months).
-- `ticks` labels every N years. Bars are spans/divs with from= and optional to=.
local function gantt(el)
  local start = tonumber(el.attributes.start)
  local stop = tonumber(el.attributes["end"])
  if not (start and stop) then return nil end
  local res = tonumber(el.attributes.res) or 1
  local tick_every = tonumber(el.attributes.ticks) or 1
  el.attributes.start, el.attributes["end"], el.attributes.res, el.attributes.ticks = nil, nil, nil, nil

  local function col(t) return math.floor((t - start) * res + 0.5) + 1 end
  local row = 0
  local function place(item)
    local from = tonumber(item.attributes.from)
    if not from then return nil end
    local to = tonumber(item.attributes.to) or stop
    item.attributes.from, item.attributes.to = nil, nil
    row = row + 1
    add_class(item.classes, "bar")
    prepend_style(item.attributes, string.format("grid-column:%d / %d;grid-row:%d;", col(from), col(to), row))
    return item
  end
  el = el:walk({ Span = place, Div = place })

  local ticks = {}
  for y = start, stop - 1, tick_every do
    table.insert(ticks, string.format(
      '<span class="gantt-tick" style="grid-column:%d / span %d;grid-row:%d;">%d</span>',
      col(y), res * tick_every, row + 1, y))
  end
  el.content:insert(pandoc.RawBlock("html", table.concat(ticks)))
  prepend_style(el.attributes, string.format("--years:%g;--cols:%d;", stop - start, (stop - start) * res))
  return el
end

-- Pandoc turns a div that opens with a heading into a <section>, which
-- reveal.js would then count as a slide. A leading empty block prevents it.
local ruled_blocks = { "col", "note", "ruled" }
local block_containers = { "cols", "steps", "stats" }

local function keep_div(el)
  if el.t == "Div" and el.content[1] and el.content[1].t == "Header" then
    el.content:insert(1, pandoc.RawBlock("html", ""))
  end
  return el
end

local function Div(el)
  if has_any(el.classes, ruled_blocks) then keep_div(el) end
  if has_any(el.classes, block_containers) then
    for _, child in ipairs(el.content) do keep_div(child) end
  end
  if el.classes:includes("gantt") then el = gantt(el) or el end
  if has_any(el.classes, no_stretch_containers) then
    el = el:walk({ Image = function(img) add_class(img.classes, "nostretch"); return img end })
  end
  return el
end

-- Meta is visited after blocks within one pass, so options are read first.
return {
  { Meta = read_options },
  { Header = Header },
  { Div = Div },
}
