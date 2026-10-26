"""
Reusable on-screen widgets and the page loop shared by every interactive screen.

Survey widgets use units="height" so circles stay round on any aspect ratio
(y spans -0.5..0.5, x spans +/- aspect/2). The experiment window itself uses
units="norm"; the listening-screen ContinuousSlider keeps norm units.
"""
from psychopy import visual, event, core

import config

TITLE_HEIGHT    = 0.03
BODY_HEIGHT     = 0.022
SMALL_HEIGHT    = 0.017
PARAGRAPH_GAP   = 1.0 * BODY_HEIGHT   # space between blank-line-separated paragraphs
LINE_SPACING    = 1.35                # line height of wrapped body text, x the font's natural one
RADIO_RADIUS    = 0.012
MAX_CARD_WIDTH  = 1.5     # caps line length on very wide screens


class Layout:
    """Card geometry derived from the window's aspect ratio (height units)."""

    def __init__(self, win):
        aspect = win.size[0] / win.size[1]
        self.card_width = min(aspect - 0.08, MAX_CARD_WIDTH)
        self.card_height = 0.94
        self.left = -self.card_width / 2 + 0.05
        self.right = self.card_width / 2 - 0.05
        self.width = self.right - self.left
        self.title_y = 0.39             # leaves room for the progress bar along the card's top edge
        self.top = 0.345                # first content line below the title
        self.footer_y = -0.42           # Next button / progress row
        self.bottom = -0.36             # content must stay above the footer
        self.next_button_pos = (self.right - 0.08, self.footer_y)


_layouts, _px_per_unit = {}, {}


def layout_for(win):
    if id(win) not in _layouts:
        _layouts[id(win)] = Layout(win)
    return _layouts[id(win)]


def _text_px_per_unit(stim):
    """Bounding-box pixels per unit, calibrated against one line of text."""
    key = (id(stim.win), stim.units, stim.height)
    if key not in _px_per_unit:
        reference = visual.TextStim(stim.win, text="Ag", height=stim.height, units=stim.units)
        _px_per_unit[key] = reference.boundingBox[1] / stim.height
    return _px_per_unit[key]


def text_height(stim):
    """Rendered height of a TextStim in its own units."""
    return stim.boundingBox[1] / _text_px_per_unit(stim)


def text_width(stim):
    """Rendered width of a TextStim's longest line, in its own units."""
    return stim.boundingBox[0] / _text_px_per_unit(stim)


def stack_paragraphs(make, text, top, gap):
    """
    Splits `text` at blank lines into one stim per paragraph, built by make(paragraph, y, bold)
    with its top edge at y, stacked downward from `top`. TextStim has no inline bold, so a
    paragraph wrapped in **...** is drawn bold as a whole. Returns (stims, y of the bottom edge).
    """
    stims, y = [], top
    for paragraph in text.strip().split("\n\n"):
        paragraph = paragraph.strip()
        bold = paragraph.startswith("**") and paragraph.endswith("**")
        stim = make(paragraph[2:-2] if bold else paragraph, y, bold)
        stims.append(stim)
        y -= text_height(stim) + gap
    return stims, y + gap


def shift_y(stims, dy):
    for stim in stims:
        stim.pos = (stim.pos[0], stim.pos[1] + dy)


# ─────────────────────────────────────────────
# KEYBOARD CONTROL
# ─────────────────────────────────────────────

class ExperimentAborted(Exception):
    """Raised by QUIT_KEY; the main script catches it, saves and shuts down cleanly."""


def poll_control_keys():
    """Call once per frame. Returns True if the testing skip key was pressed."""
    keys = event.getKeys([config.QUIT_KEY, config.SKIP_KEY])
    if config.QUIT_KEY in keys:
        raise ExperimentAborted()
    return config.ALLOW_SKIP and config.SKIP_KEY in keys


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

class SpacedTextStim(visual.TextStim):
    """TextStim with adjustable line spacing (a multiple of the font's natural line height),
    which TextStim lacks: re-applies pyglet's line_spacing style whenever the text is laid out.
    boundingBox, and so text_height(), includes the extra spacing."""

    def __init__(self, *args, lineSpacing=1.0, **kwargs):
        self.lineSpacing = lineSpacing   # set before TextStim.__init__ lays out the text
        super().__init__(*args, **kwargs)

    def _setTextShaders(self, value=None):
        super()._setTextShaders(value)
        label = self._pygletTextObj
        if label is not None and label.document.text and self.lineSpacing != 1.0:
            font = label.document.get_font(0)
            label.set_style("line_spacing", (font.ascent - font.descent) * self.lineSpacing)


def make_text(win, text, pos, height=BODY_HEIGHT, color=config.TEXT_COLOR,
              wrap=None, align="center", line_spacing=1.0, **kwargs):
    return SpacedTextStim(win, text=text, pos=pos, height=height, color=color,
                          wrapWidth=wrap or layout_for(win).width, font=config.FONT, units="height",
                          alignText=align, anchorHoriz=align, lineSpacing=line_spacing, **kwargs)


def mouse_pos_height(mouse, win):
    """Mouse position in height units; assumes the window uses units="norm"."""
    x, y = mouse.getPos()
    aspect = win.size[0] / win.size[1]
    return x * aspect / 2, y / 2


def _hit(pos, center, half_size):
    return (abs(pos[0] - center[0]) <= half_size[0]
            and abs(pos[1] - center[1]) <= half_size[1])


# ─────────────────────────────────────────────
# WIDGETS  (each implements draw() and handle_click(pos))
# ─────────────────────────────────────────────

class Button:

    def __init__(self, win, text, pos=None, size=(0.16, 0.055)):
        pos = pos or layout_for(win).next_button_pos
        self.pos, self.half_size = pos, (size[0] / 2, size[1] / 2)
        self.enabled = True
        self.box = visual.Rect(win, width=size[0], height=size[1], pos=pos,
                               units="height", lineColor=None)
        self.label = make_text(win, text, pos, bold=True)

    def contains(self, pos):
        return self.enabled and _hit(pos, self.pos, self.half_size)

    def handle_click(self, pos):
        pass

    def draw(self):
        self.box.fillColor = config.ACCENT_COLOR if self.enabled else config.DISABLED_COLOR
        self.label.color = config.TEXT_COLOR if self.enabled else config.MUTED_COLOR
        self.box.draw()
        self.label.draw()


class AudioPlayButton(Button):
    """Restarts the sound on every click; `played` becomes True after the first."""

    def __init__(self, win, audio, pos, text="Play sound"):
        super().__init__(win, text, pos, size=(0.22, 0.06))
        self.audio, self.played = audio, False

    def handle_click(self, pos):
        if self.contains(pos):
            self.audio.stop()
            self.audio.play()
            self.played = True


class RadioGroup:
    """One single-choice question; `value` is the chosen option index or None."""

    def __init__(self, win, positions, labels=None, label_offset=(0, -0.035),
                 label_align="center", label_wrap=0.12, hit_half_size=(0.03, 0.03),
                 on_change=None):
        self.positions, self.hit_half_size = positions, hit_half_size
        self.on_change = on_change
        self.value = None
        self.rings = [visual.Circle(win, radius=RADIO_RADIUS, pos=p, edges=48,
                                    units="height", lineWidth=2,
                                    lineColor=config.BORDER_COLOR, fillColor=None)
                      for p in positions]
        self.dot = visual.Circle(win, radius=RADIO_RADIUS * 0.55, edges=48, units="height",
                                 lineColor=None, fillColor=config.ACCENT_COLOR)
        self.labels = [make_text(win, label, (p[0] + label_offset[0], p[1] + label_offset[1]),
                                 height=SMALL_HEIGHT, wrap=label_wrap, align=label_align)
                       for p, label in zip(positions, labels or [])]

    @classmethod
    def vertical(cls, win, top_left, labels, spacing=0.055, **kwargs):
        """Options stacked downwards with labels to the right of the circles."""
        x, y = top_left
        return cls(win, [(x, y - spacing * i) for i in range(len(labels))], labels=labels,
                   label_offset=(0.03, 0), label_align="left", label_wrap=0.8,
                   hit_half_size=(0.3, spacing / 2 - 0.002), **kwargs)

    def handle_click(self, pos):
        for i, p in enumerate(self.positions):
            if _hit(pos, p, self.hit_half_size) and i != self.value:
                self.value = i
                if self.on_change:
                    self.on_change(i)

    def draw(self):
        for i, ring in enumerate(self.rings):
            ring.lineColor = config.ACCENT_COLOR if i == self.value else config.BORDER_COLOR
            ring.draw()
        for label in self.labels:
            label.draw()
        if self.value is not None:
            self.dot.pos = self.positions[self.value]
            self.dot.draw()


class TextEntry:
    """Single-line text field; focus follows clicks."""

    def __init__(self, win, pos, width=0.3):
        self.pos, self.half_size = pos, (width / 2, 0.025)
        self.box = visual.TextBox2(win, text="", editable=True, pos=pos,
                                   size=(width, 0.05), units="height",
                                   letterHeight=BODY_HEIGHT, color=config.TEXT_COLOR,
                                   fillColor=config.STRIPE_COLOR, borderColor=config.BORDER_COLOR,
                                   font=config.FONT, alignment="left", padding=0.01)

    @property
    def value(self):
        return self.box.text.replace("\n", " ").strip()

    def focus(self, has_focus=True):
        self.box.hasFocus = has_focus

    def handle_click(self, pos):
        self.focus(_hit(pos, self.pos, self.half_size))

    def draw(self):
        self.box.borderColor = config.ACCENT_COLOR if self.box.hasFocus else config.BORDER_COLOR
        self.box.draw()


class RatingSlider:
    """Discrete rating scale (PsychoPy Slider); `value` is the chosen tick or None."""

    def __init__(self, win, ticks, pos=(0, 0), width=0.8):
        self.slider = visual.Slider(win, ticks=ticks, labels=[str(t) for t in ticks],
                                    startValue=None, pos=pos, size=(width, 0.045),
                                    units="height", style="rating", granularity=1,
                                    color=config.TEXT_COLOR, fillColor=config.ACCENT_COLOR,
                                    borderColor=config.BORDER_COLOR, labelColor=config.TEXT_COLOR,
                                    font=config.FONT, labelHeight=BODY_HEIGHT)

    @property
    def value(self):
        return self.slider.getRating()

    def handle_click(self, pos):
        pass   # visual.Slider reads the mouse itself while drawing

    def draw(self):
        self.slider.draw()


class ScrollArea:
    """
    Stims scrolled by the mouse wheel / trackpad between viewport_top and viewport_bottom
    (height units). Text scrolled out of view is hidden by masks in the card and window
    colours, so draw this before anything that sits above or below the viewport.
    """
    SCROLL_STEP = 0.04   # height units per wheel notch

    def __init__(self, win, stims, viewport_top, viewport_bottom, content_bottom):
        layout = layout_for(win)
        self.win, self.stims, self.offset = win, stims, 0.0
        self.max_offset = max(0.0, viewport_bottom - content_bottom)
        self.mouse = event.Mouse(win=win)
        self.mouse.getWheelRel()   # discard scrolling done on earlier pages
        card_top, far = layout.card_height / 2, 10

        def mask(top, bottom, width, **color):
            return visual.Rect(win, width=width, height=top - bottom, pos=(0, (top + bottom) / 2),
                               units="height", lineColor=None, **color)

        card = dict(fillColor=config.CARD_COLOR)
        background = dict(fillColor=win.color, colorSpace=win.colorSpace)
        self.masks = [
            mask(card_top, viewport_top, layout.card_width, **card),
            mask(viewport_bottom, -card_top, layout.card_width, **card),
            mask(far, card_top, far, **background),
            mask(-card_top, -far, far, **background),
        ]
        viewport = viewport_top - viewport_bottom
        self.track_top, self.track_height = viewport_top, viewport
        x = layout.right + 0.03
        self.track = visual.Rect(win, width=0.006, height=viewport, units="height",
                                 pos=(x, viewport_top - viewport / 2),
                                 fillColor=config.STRIPE_COLOR, lineColor=None)
        self.thumb = visual.Rect(win, width=0.006, units="height", pos=(x, 0),
                                 height=viewport * viewport / (viewport + self.max_offset),
                                 fillColor=config.MUTED_COLOR, lineColor=None)

    @property
    def scrollable(self):
        return self.max_offset > 0

    def handle_click(self, pos):
        pass

    def draw(self):
        if self.scrollable:
            new = min(max(self.offset - self.mouse.getWheelRel()[1] * self.SCROLL_STEP, 0.0),
                      self.max_offset)
            shift_y(self.stims, new - self.offset)
            self.offset = new
        for stim in self.stims:
            stim.draw()
        for m in self.masks:
            m.draw()
        if self.scrollable:
            free = self.track_height - self.thumb.height
            self.thumb.pos = (self.thumb.pos[0], self.track_top - self.thumb.height / 2
                              - free * self.offset / self.max_offset)
            self.track.draw()
            self.thumb.draw()


class Conditional:
    """Shows (and enables) a widget or stimulus only while condition() is truthy."""

    def __init__(self, item, condition):
        self.item, self.condition = item, condition

    def handle_click(self, pos):
        if self.condition() and hasattr(self.item, "handle_click"):
            self.item.handle_click(pos)

    def draw(self):
        if self.condition():
            self.item.draw()


class ContinuousSlider:
    """Click/drag slider from vmin to vmax in norm units. Replaces visual.Slider for the
    continuous rating, whose getRating() only ever returned the start value."""

    def __init__(self, win, mouse, pos=(0, -0.45), width=1.5,
                 vmin=config.CONTINUOUS_SCALE_MIN, vmax=config.CONTINUOUS_SCALE_MAX,
                 start=config.CONTINUOUS_SCALE_START, click_height=0.25,
                 show_labels=True, show_marker=True):
        self.win, self.mouse = win, mouse
        self.vmin, self.vmax, self.start = vmin, vmax, start
        self.width, self.y = width, pos[1]
        self.x0 = pos[0] - width / 2
        self.click_height = click_height     # +/- vertical tolerance for starting a drag
        self.line = visual.Rect(win, width=width, height=0.012, pos=pos,
                                fillColor="white", lineColor="white")
        self.ticks, self.labels = [], []
        for val, text in [(vmin, f"Very Unpleasant\n{vmin}"),
                          ((vmin + vmax) / 2, f"Neutral\n{(vmin + vmax) // 2}"),
                          (vmax, f"Very Pleasant\n{vmax}")]:
            x = self._val_to_x(val)
            self.ticks.append(visual.Rect(win, width=0.006, height=0.06, pos=(x, self.y),
                                          fillColor="white", lineColor="white"))
            if show_labels:
                self.labels.append(visual.TextStim(win, text=text, pos=(x, self.y - 0.12),
                                                   height=0.04, color=[0.6, 0.6, 0.6],
                                                   wrapWidth=0.5))
        self.show_marker = show_marker
        self.marker = visual.Rect(win, width=0.02, height=0.1, pos=(0, self.y),
                                  fillColor=config.ACCENT_COLOR, lineColor="white")
        self.reset()

    def _val_to_x(self, v):
        return self.x0 + (v - self.vmin) / (self.vmax - self.vmin) * self.width

    def reset(self):
        self.value, self.touched, self._dragging = self.start, False, False
        self.marker.pos = (self._val_to_x(self.value), self.y)

    def update(self):
        """Call once per frame, before getRating()."""
        pressed = self.mouse.getPressed()[0]
        x, y = self.mouse.getPos()
        if pressed:
            if (not self._dragging
                    and abs(y - self.y) <= self.click_height
                    and self.x0 - 0.05 <= x <= self.x0 + self.width + 0.05):
                self._dragging = True
            if self._dragging:
                frac = min(max((x - self.x0) / self.width, 0.0), 1.0)
                new = round(self.vmin + frac * (self.vmax - self.vmin))   # integers, as in Qualtrics
                if config.DEBUG_SLIDER and new != self.value:
                    print(f"slider value={new}")
                self.value, self.touched = new, True
                self.marker.pos = (self._val_to_x(new), self.y)
        else:
            self._dragging = False

    def getRating(self):
        """None until the participant has touched the slider."""
        return self.value if self.touched else None

    def draw(self):
        self.line.draw()
        for t in self.ticks:
            t.draw()
        for l in self.labels:
            l.draw()
        if self.show_marker:
            self.marker.draw()


# ─────────────────────────────────────────────
# PAGE LOOP
# ─────────────────────────────────────────────

class SessionProgress:
    """Share of the session completed, drawn as a thin bar at the top of every card page.
    The session sets `total` and calls step() after each screen or trial; total = 0 hides it."""

    def __init__(self):
        self.done, self.total = 0, 0
        self._track = self._fill = None

    def step(self):
        self.done += 1

    def draw(self, win):
        if not self.total:
            return
        layout = layout_for(win)
        if self._track is None:
            y = layout.card_height / 2 - 0.02
            self._track = visual.Rect(win, width=layout.width, height=0.006, pos=(0, y),
                                      units="height", fillColor=config.STRIPE_COLOR, lineColor=None)
            self._fill = visual.Rect(win, width=layout.width, height=0.006, pos=(0, y),
                                     units="height", fillColor=config.ACCENT_COLOR, lineColor=None)
        self._track.draw()
        filled = layout.width * min(self.done / self.total, 1.0)
        if filled > 0:
            self._fill.width = filled
            self._fill.pos = (layout.left + filled / 2, self._track.pos[1])
            self._fill.draw()


session_progress = SessionProgress()


def run_page(win, widgets=(), is_complete=lambda: True, next_label="Next",
             decorations=(), progress_text=""):
    """
    Draw a card with widgets until the participant clicks an enabled Next button.
    Returns (page_rt, skipped): seconds from first draw to submit, and whether the
    testing skip key was used (widget values may then still be None).
    """
    mouse = event.Mouse(win=win)
    layout = layout_for(win)
    card = visual.Rect(win, width=layout.card_width, height=layout.card_height, units="height",
                       fillColor=config.CARD_COLOR, lineColor=None)
    progress = make_text(win, progress_text, (layout.left, layout.footer_y),
                         height=SMALL_HEIGHT, color=config.MUTED_COLOR, align="left")
    next_button = Button(win, next_label)
    page_clock = core.Clock()
    win.callOnFlip(page_clock.reset)
    was_pressed = True   # ignore a click held over from the previous page
    event.clearEvents()

    while True:
        pressed = mouse.getPressed()[0]
        clicked = pressed and not was_pressed
        was_pressed = pressed
        pos = mouse_pos_height(mouse, win)

        if clicked:
            for widget in widgets:
                widget.handle_click(pos)
        next_button.enabled = bool(is_complete())

        card.draw()
        for stim in decorations:
            stim.draw()
        session_progress.draw(win)   # after decorations, which may mask the card edges (ScrollArea)
        for widget in widgets:
            widget.draw()
        progress.draw()
        next_button.draw()
        win.flip()

        if clicked and next_button.contains(pos):
            page_rt = page_clock.getTime()
            core.wait(0.2)
            return page_rt, False
        if poll_control_keys():
            return page_clock.getTime(), True
