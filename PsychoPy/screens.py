"""
Every participant-facing screen, built from the widgets in ui.py.

Positions are derived from ui.Layout (window aspect ratio) and measured text
heights, and questionnaire items are paginated by how many fit on screen.
Questionnaire screens return ItemResponse rows ready for SessionLogs.write_responses();
an unanswered (skipped) item has response = None, which is logged as NA.
"""
from psychopy import visual, event, core

import config
import ui
from data_logging import ItemResponse

ROW_PADDING   = 0.03    # vertical padding inside a matrix row
SECTION_GAP   = 0.03
READING_WIDTH = 0.9     # max line width on text-only pages (height units)
PROMPT_WIDTH  = 0.8     # column for rating prompts; matches the RatingSlider width


def _choice_response(item_id, item_text, options, index, page_rt):
    if index is None:
        return ItemResponse(item_id, item_text, None, None, page_rt)
    return ItemResponse(item_id, item_text, index + 1, options[index], page_rt)


def _title(win, text):
    return ui.make_text(win, text, (0, ui.layout_for(win).title_y), height=ui.TITLE_HEIGHT, bold=True)


def _header(win, title):
    """([title stim] or [], y where content starts); with no title, content moves up into its space."""
    layout = ui.layout_for(win)
    if title is None:
        return [], layout.title_y + ui.TITLE_HEIGHT / 2
    return [_title(win, title)], layout.top


def _paragraph(win, text, y, anchor="top", **kwargs):
    return ui.make_text(win, text, (ui.layout_for(win).left, y), align="left",
                        anchorVert=anchor, line_spacing=ui.LINE_SPACING, **kwargs)


def _paragraphs(win, text, top):
    """Left-aligned body text, one stim per paragraph (see ui.stack_paragraphs)."""
    return ui.stack_paragraphs(lambda p, y, bold: _paragraph(win, p, y, bold=bold),
                               text, top, ui.PARAGRAPH_GAP)


def _all_answered(widgets):
    return lambda: all(w.value is not None for w in widgets)


def _paginate(heights, available):
    """Greedily groups item indices into pages whose summed heights fit `available`."""
    pages, current, used = [], [], 0.0
    for i, h in enumerate(heights):
        if current and used + h > available:
            pages.append(current)
            current, used = [], 0.0
        current.append(i)
        used += h
    if current:
        pages.append(current)
    return pages


def _page_label(page, n_pages):
    return f"Page {page + 1} of {n_pages}" if n_pages > 1 else ""

# ─────────────────────────────────────────────
# GENERAL PAGES
# ─────────────────────────────────────────────

def _centered_block(win, title, body, below=0.0):
    """
    Title and left-aligned paragraphs as one block centred on the card, with `below` height
    units reserved underneath for a widget. The text column is as wide as its longest line
    (at most READING_WIDTH), so short text is centred too. Top-aligned if the block is too tall.
    Returns (stims, y of the reserved space's top edge).
    """
    layout = ui.layout_for(win)
    width = min(layout.width, READING_WIDTH)
    stims, y = [], 0.0
    if title is not None:
        title_stim = ui.make_text(win, title, (0, y), height=ui.TITLE_HEIGHT, bold=True,
                                  anchorVert="top")
        stims.append(title_stim)
        y -= ui.text_height(title_stim) + SECTION_GAP
    if body is not None:
        body_stims, y = ui.stack_paragraphs(
            lambda p, py, bold: ui.make_text(win, p, (-width / 2, py), align="left",
                                             anchorVert="top", wrap=width, bold=bold,
                                             line_spacing=ui.LINE_SPACING),
            body, y, ui.PARAGRAPH_GAP)
        indent = (width - max(ui.text_width(s) for s in body_stims)) / 2
        for stim in body_stims:
            stim.pos = (stim.pos[0] + indent, stim.pos[1])
        stims += body_stims
    top = layout.title_y + ui.TITLE_HEIGHT / 2
    shift = min((top + layout.bottom - y + below) / 2, top)   # y - below = -(block height)
    ui.shift_y(stims, shift)
    return stims, y + shift


def show_text_page(win, title, body, next_label="Next"):
    """Text-only page, laid out by _centered_block."""
    stims, _ = _centered_block(win, title, body)
    return ui.run_page(win, next_label=next_label, decorations=stims)


def run_consent(win, consent_text, agreement_text):
    """Returns (consented, [ItemResponse]). Skipping counts as consent (testing only)."""
    layout = ui.layout_for(win)
    options = ["I consent", "I do not consent"]
    choice = ui.RadioGroup.vertical(win, (layout.left + 0.02, layout.bottom + 0.075), options)
    agreement = _paragraph(win, agreement_text, layout.bottom + 0.11, anchor="bottom")
    body, body_bottom = _paragraphs(win, consent_text, layout.top)
    viewport_bottom = layout.bottom + 0.11 + ui.text_height(agreement) + SECTION_GAP
    scroll = ui.ScrollArea(win, body, layout.top, viewport_bottom, body_bottom)
    page_rt, skipped = ui.run_page(win, [choice], _all_answered([choice]),
                                   decorations=[scroll, _title(win, "Consent Form"), agreement],
                                   progress_text="Scroll to read the full form" if scroll.scrollable else "")
    consented = skipped or choice.value == 0
    return consented, [_choice_response("consent", agreement_text, options, choice.value, page_rt)]


def run_audio_check(win, audio, body):
    stims, body_bottom = _centered_block(win, "Volume Adjustment", body, below=0.13)
    play_button = ui.AudioPlayButton(win, audio, pos=(0, body_bottom - 0.08))
    ui.run_page(win, [play_button], lambda: play_button.played, decorations=stims)
    audio.stop()


def show_baseline_screen(win, duration, message):
    """`message` at the listening-screen instruction position above a bare, non-interactive
    copy of the listening-screen slider, so layout and luminance match the listening screen."""
    slider = ui.ContinuousSlider(win, event.Mouse(win=win), show_labels=False, show_marker=False)
    message_stim = visual.TextStim(win, text=message, pos=(0, 0.55), height=0.05,
                                   color="white", wrapWidth=1.7, alignText="center")
    clock = core.Clock()
    win.callOnFlip(clock.reset)
    while clock.getTime() < duration:
        message_stim.draw()
        slider.draw()
        win.flip()
        if ui.poll_control_keys():
            return

# ─────────────────────────────────────────────
# QUESTIONNAIRES
# ─────────────────────────────────────────────

def run_demographics(win, gender_options, min_age=18, max_age=120):
    layout = ui.layout_for(win)
    age_question, gender_question = "What is your age?", "What is your gender?"
    age_label = _paragraph(win, age_question, layout.top - 0.03)
    age_y = layout.top - 0.03 - ui.text_height(age_label) - 0.045
    age_entry = ui.TextEntry(win, pos=(layout.left + 0.15, age_y), width=0.3)
    gender_label = _paragraph(win, gender_question, age_y - 0.1)
    gender_choice = ui.RadioGroup.vertical(
        win, (layout.left + 0.02, age_y - 0.1 - ui.text_height(gender_label) - 0.045), gender_options)

    def age_is_valid():
        return age_entry.value.isdigit() and min_age <= int(age_entry.value) <= max_age

    age_error = ui.make_text(win, f"Please enter a whole number between {min_age} and {max_age}.",
                             (layout.left + 0.33, age_y), height=ui.SMALL_HEIGHT,
                             color=config.ERROR_COLOR, align="left")
    decorations = [_title(win, "About You"), age_label, gender_label,
                   ui.Conditional(age_error, lambda: age_entry.value and not age_is_valid())]
    page_rt, _ = ui.run_page(win, [age_entry, gender_choice],
                             lambda: age_is_valid() and gender_choice.value is not None,
                             decorations=decorations)
    age = int(age_entry.value) if age_is_valid() else None
    return [
        ItemResponse("age", age_question, age, age, page_rt),
        _choice_response("gender", gender_question, gender_options, gender_choice.value, page_rt),
    ]


def _paginate_in_order(heights, available, order):
    """_paginate over items shown in `order` (indices into heights; None = as listed)."""
    order = list(range(len(heights))) if order is None else order
    return [[order[p] for p in page] for page in _paginate([heights[i] for i in order], available)]


def run_choice_questions(win, id_prefix, title, questions, first_item_num=1, order=None):
    """
    Single-choice questions stacked vertically, each with its own horizontal options
    (Qualtrics "multiple choice"), paginated to fit. questions: [(text, [options])].
    order: display order as indices into questions; item IDs always follow the listed order.
    """
    layout = ui.layout_for(win)
    title_stims, top = _header(win, title)
    question_stims = [_paragraph(win, text, 0) for text, _ in questions]
    option_block = ui.RADIO_RADIUS * 2 + 0.05       # radio row + its labels underneath
    block_heights = [ui.text_height(stim) + 0.02 + option_block + SECTION_GAP
                     for stim in question_stims]
    pages = _paginate_in_order(block_heights, top - layout.bottom, order)

    responses = []
    for page, indices in enumerate(pages):
        decorations, widgets, y = list(title_stims), [], top
        for i in indices:
            text, options = questions[i]
            question_stims[i].pos = (layout.left, y)
            decorations.append(question_stims[i])
            radio_y = y - ui.text_height(question_stims[i]) - 0.02 - ui.RADIO_RADIUS
            spacing = layout.width / len(options)
            xs = [layout.left + spacing * (k + 0.5) for k in range(len(options))]
            widgets.append(ui.RadioGroup(win, [(x, radio_y) for x in xs], labels=options,
                                         label_wrap=spacing - 0.01,
                                         hit_half_size=(spacing / 2, 0.035)))
            y -= block_heights[i]
        page_rt, _ = ui.run_page(win, widgets, _all_answered(widgets), decorations=decorations,
                                 progress_text=_page_label(page, len(pages)))
        responses += [_choice_response(f"{id_prefix}_{first_item_num + i:02d}", questions[i][0],
                                       questions[i][1], w.value, page_rt)
                      for i, w in zip(indices, widgets)]
    return responses


def run_matrix_questionnaire(win, id_prefix, title, instruction, items, scale_labels, order=None):
    """
    Qualtrics "matrix table": statements as rows, one shared agreement scale as
    columns, paginated to fit the screen. Every item must be answered (force response).
    order: display order as indices into items; item IDs always follow the listed order.
    """
    layout = ui.layout_for(win)
    text_width = layout.width * 0.42
    scale_left = layout.left + text_width + 0.03
    col_width = (layout.right - scale_left) / len(scale_labels)
    col_xs = [scale_left + col_width * (i + 0.5) for i in range(len(scale_labels))]

    title_stims, top = _header(win, title)
    instruction_stim = ui.make_text(win, instruction.strip(), (layout.left, top),
                                    height=ui.SMALL_HEIGHT, color=config.MUTED_COLOR,
                                    align="left", anchorVert="top", line_spacing=ui.LINE_SPACING)
    labels_top = top - ui.text_height(instruction_stim) - SECTION_GAP
    label_stims = [ui.make_text(win, label, (x, labels_top), height=ui.SMALL_HEIGHT,
                                color=config.MUTED_COLOR, wrap=col_width - 0.01, anchorVert="top")
                   for x, label in zip(col_xs, scale_labels)]
    rows_top = labels_top - max(ui.text_height(s) for s in label_stims) - 0.02
    header = title_stims + [instruction_stim] + label_stims

    item_stims = [ui.make_text(win, item, (layout.left + 0.02, 0), align="left", wrap=text_width)
                  for item in items]
    row_heights = [max(0.06, ui.text_height(stim) + ROW_PADDING) for stim in item_stims]
    pages = _paginate_in_order(row_heights, rows_top - layout.bottom, order)

    responses = []
    for page, indices in enumerate(pages):
        decorations, widgets, y = list(header), [], rows_top
        for row, i in enumerate(indices):
            center_y = y - row_heights[i] / 2
            if row % 2 == 0:
                decorations.append(visual.Rect(win, width=layout.card_width - 0.04,
                                               height=row_heights[i], pos=(0, center_y),
                                               units="height", fillColor=config.STRIPE_COLOR,
                                               lineColor=None))
            item_stims[i].pos = (layout.left + 0.02, center_y)
            decorations.append(item_stims[i])
            widgets.append(ui.RadioGroup(win, [(x, center_y) for x in col_xs],
                                         hit_half_size=(col_width / 2, row_heights[i] / 2)))
            y -= row_heights[i]
        page_rt, _ = ui.run_page(win, widgets, _all_answered(widgets), decorations=decorations,
                                 progress_text=_page_label(page, len(pages)))
        responses += [_choice_response(f"{id_prefix}_{i + 1:02d}", items[i], scale_labels,
                                       w.value, page_rt)
                      for i, w in zip(indices, widgets)]
    return responses

# ─────────────────────────────────────────────
# TRIAL SCREENS
# ─────────────────────────────────────────────

class ListeningScreen:
    """Layout shown while a stimulus plays (norm units)."""

    def __init__(self, win, instruction_text):
        self.slider = ui.ContinuousSlider(win, event.Mouse(win=win))
        instruction, bottom = ui.stack_paragraphs(
            lambda p, y, bold: visual.TextStim(win, text=p, pos=(-0.75, y), height=0.05, color="white",
                                               wrapWidth=1.5, alignText="left", anchorHoriz="left",
                                               anchorVert="top", bold=bold),
            instruction_text, 0, 0.03)
        ui.shift_y(instruction, 0.55 - bottom / 2)   # block stays centred at y = 0.55
        self.texts = instruction + [
            visual.TextStim(win, text="Rating", pos=(-0.75, -0.33), height=0.04,
                            color=[0.6, 0.6, 0.6], anchorHoriz="left"),
            visual.TextStim(win, text="You will be able to continue once the track has finished playing.",
                            pos=(0, -0.75), height=0.04, color=[0.6, 0.6, 0.6]),
        ]

    def reset(self):
        self.slider.reset()

    def update_and_draw(self):
        """Draws one frame; returns the current rating (None until touched)."""
        for text in self.texts:
            text.draw()
        self.slider.update()
        self.slider.draw()
        return self.slider.getRating()


def run_overall_rating(win, prompt_text):
    """1-6 rating; Submit stays disabled until a value is chosen. Returns (rating, rt)."""
    rating = ui.RatingSlider(win, config.OVERALL_SCALE, pos=(0, -0.05))
    prompt, bottom = ui.stack_paragraphs(
        lambda p, y, bold: ui.make_text(win, p, (-PROMPT_WIDTH / 2, y), align="left",
                                        anchorVert="top", wrap=PROMPT_WIDTH, bold=bold,
                                        line_spacing=ui.LINE_SPACING),
        prompt_text, 0, ui.PARAGRAPH_GAP)
    ui.shift_y(prompt, 0.05 - bottom)   # prompt block ends just above the rating scale
    page_rt, _ = ui.run_page(win, [rating], lambda: rating.value is not None,
                             next_label="Submit", decorations=prompt)
    return rating.value, page_rt


def run_familiarity(win):
    """Familiarity check (exclusion criterion). Returns (recognized "yes"/"no", song name)."""
    left = -PROMPT_WIDTH / 2
    name_entry = ui.TextEntry(win, pos=(0, -0.12), width=PROMPT_WIDTH)
    radio_x = left + ui.RADIO_RADIUS
    choice = ui.RadioGroup(win, [(radio_x, 0.1), (radio_x + 0.2, 0.1)], labels=["Yes", "No"],
                           label_offset=(0.03, 0), label_align="left", label_wrap=0.2,
                           hit_half_size=(0.1, 0.03),
                           on_change=lambda i: name_entry.focus(i == 0))
    recognized_yes = lambda: choice.value == 0

    def text(s, y, **kwargs):
        return ui.make_text(win, s, (left, y), align="left", wrap=PROMPT_WIDTH,
                            line_spacing=ui.LINE_SPACING, **kwargs)

    decorations = [
        text("Did you recognize this as a specific piece of music?", 0.3),
        text("Answer \"Yes\" only if you are sure. Not recognizing it is completely normal.",
             0.24, height=ui.SMALL_HEIGHT, color=config.MUTED_COLOR),
        ui.Conditional(text("Which piece was it? (title and/or artist)", -0.05),
                       recognized_yes),
    ]
    # "Yes" needs a non-empty answer before Submit is enabled
    is_complete = lambda: choice.value is not None and (not recognized_yes() or name_entry.value.strip())
    ui.run_page(win, [choice, ui.Conditional(name_entry, recognized_yes)],
                is_complete, next_label="Submit", decorations=decorations)
    name_entry.focus(False)
    if choice.value is None:
        return None, None
    return ("yes", name_entry.value) if recognized_yes() else ("no", "")
