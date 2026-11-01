"""
Participant-facing text and questionnaire items.
"""

# ─────────────────────────────────────────────
# CONSENT / INSTRUCTIONS 
# ─────────────────────────────────────────────

# Body text on screens is split into paragraphs at blank lines ("\n\n"); a paragraph
# wrapped in **...** is shown in bold (only whole paragraphs can be bold).

# Wording is the IRB-approved consent text; only paragraph breaks were added
CONSENT_TEXT = (
    "You are being asked to be a volunteer in a research study in which you will listen to "
    "sequences of chords while making continuous ratings of your experience. You will be fitted "
    "with a lightweight eye-tracking headset that measures your pupil activity while you complete "
    "the task. They fit like regular glasses and have no sensors but only cameras measuring your "
    "pupils. Because the headset cannot be worn over eyeglasses, you must be able to see the "
    "computer screen clearly without corrective eyeglasses or while wearing contact lenses in "
    "order to participate. You will be given further instructions in person and also written "
    "explanations on how to make these ratings on the next page.\n\n"

    "You can earn 1.0 SONA credit upon completing this study. The study will take approximately "
    "60 minutes in total.\n\n"

    "The purpose of this study is to explore how people experience pleasantness when listening to "
    "different chord progressions. Your ratings in this study will be completely anonymized, so "
    "your responses are not tied to your identity in any way. The risks involved are no greater "
    "than those involved in using a computer or listening to music in your everyday life.\n\n"

    "We will comply with any applicable laws and regulations regarding confidentiality. To make "
    "sure that this research is being carried out in the proper way, the Georgia Institute of "
    "Technology IRB may review study records. The Office of Human Research Protections may also "
    "look at study records.\n\n"

    "If you have any questions about the study, you may contact Ling Qi at lqi60@gatech.edu or "
    "the PI, Dr. Claire Arthur at claire.arthur@gatech.edu. If you have any questions about your "
    "rights as a research subject, you may contact the Georgia Tech IRB at irb@gatech.edu.\n\n"

    "Your participation in this study is voluntary. You do not have to be in this study if you do "
    "not want to be. You have the right to change your mind and leave the study at any time "
    "without giving any reason. However, if you are participating through SONA and you do not "
    "complete the experiment, you will not receive any credit.\n\n"

    "You do not waive any of your legal rights by agreeing to be in the study. By continuing in "
    "this study, you are providing your consent to participate. Your answers are extremely "
    "valuable to us, and we thank you for participating in this study."
)

CONSENT_AGREEMENT = (
    "By clicking the button below, I affirm that I am at least 18 years of age, that I have "
    "read and understood the above consent document, and that I willingly give my consent "
    "to participate in this study."
)

NO_CONSENT_TEXT = "You have chosen not to participate. Please let the experimenter know."

AUDIO_CHECK_TEXT = (
    "Click \"Play sound\" and adjust the volume to a comfortable level. "
    "You can replay the sound as often as you like."
)

LISTENING_INSTRUCTIONS = (
    "You will listen to 38 musical sequences, each approximately 1.5 minutes long. You will "
    "complete a questionnaire after the first half of the sequences and another at the end.\n\n"

    "Before each sequence, you will hear one example chord followed by four short clicks as a "
    "countdown. The sequence begins immediately after the countdown.\n\n"

    "While the sequence plays, move the slider continuously to indicate how pleasant or "
    "unpleasant you find the sounds from moment to moment.\n\n"

    "Please try to use the full range of the slider. Over the course of the experiment, try to select "
    "the extreme ends of the scale (“Very Unpleasant” or “Very Pleasant”) at least 5 times.\n\n"

    "**Evaluate “pleasantness” in terms of aesthetics (how much you like the sound) "
    "rather than emotions.**\n\n"

    "When the sequence ends, you will rate its overall pleasantness and arousal.\n\n"

    "Please keep your head still and your eyes on the screen while the music plays.\n\n"

    "Click “Next” to continue."
)

LISTENING_SCREEN_TEXT = (
    "After the countdown, keep moving the slider to indicate how pleasant or unpleasant "
    "you find the sounds as you listen.\n\n"
    "**Evaluate “pleasantness” in terms of aesthetics rather than emotions.**"
)

OVERALL_PLEASANTNESS_PROMPT = (
    "How pleasant or unpleasant did you find that sequence overall?\n\n"
    "**Evaluate “pleasantness” in terms of aesthetics rather than emotions.**\n\n"
    "(1 = Very unpleasant,  6 = Very pleasant)"
)

OVERALL_AROUSAL_PROMPT = (
    "How arousing did you find that sequence overall?\n\n"
    "**Evaluate “arousal” as how calm or energetic you perceive the music to be, regardless of your own mood.**\n\n"
    "(1 = Very relaxing or dull,  6 = Very exciting or tense)"
)

PRACTICE_INTRO = (
    "Let's start with one short practice sequence so you can get used to the task. "
    "If you have any questions about the task, you are welcome to ask the experimenter at any time."
)

# Shown during the pupil baseline; deliberately reads like a loading message, not an instruction
BASELINE_MESSAGE = "Preparing the experiment, please wait..."

TRIAL_BASELINE_MESSAGE = ""   # shown before each sequence

MAIN_TASK_INTRO = (
    "The practice is over. The main listening task starts now.\n\n"
    "If anything about the task is unclear, please ask the experimenter before you click “Start”."
)

FIRST_HALF_DONE = (
    "You have finished the first half of the listening task.\n\n"
    "Next, please answer a few questions about yourself."
)

SECOND_HALF_INTRO = "Thank you! The second half of the listening task starts now."

FINAL_QUESTIONNAIRE_INTRO = "The listening task is complete. Finally, please answer a few questions about yourself."

# ─────────────────────────────────────────────
# DEMOGRAPHICS
# ─────────────────────────────────────────────

GENDER_OPTIONS = ["Male", "Female", "Non-binary / third gender", "Prefer not to say"]

# ─────────────────────────────────────────────
# BARCELONA MUSIC REWARD QUESTIONNAIRE (BMRQ) — 20 items, 5-point scale
# ─────────────────────────────────────────────

MATRIX_INSTRUCTION = (   
"""
For each item, indicate how much you agree or disagree with what the item says. Please respond to all the items; do not leave any blank. Please be as accurate and honest as you can be. Respond to each item as if it were the only item. That is, do not worry about being consistent in your responses.
""")

BMRQ_SCALE = ["Completely disagree", "Disagree", "Neither agree nor disagree", "Agree", "Completely agree"]

BMRQ_ITEMS = [
    "When I share music with someone I feel a special connection with that person.",
    "In my free time I hardly listen to music.",
    "I like to listen to music that contains emotion.",
    "Music keeps me company when I'm alone.",
    "I don't like to dance, not even with music I like.",
    "Music makes me bond with other people.",
    "I inform myself about music I like.",
    "I get emotional listening to certain pieces of music.",
    "Music calms and relaxes me.",
    "Music often makes me dance.",
    "I'm always looking for new music.",
    "I can become tearful or cry when I listen to a melody that I like very much.",
    "I like to sing or play an instrument with other people.",
    "Music helps me chill out.",
    "I can't help humming or singing along to music that I like.",
    "At a concert I feel connected to the performers and the audience.",
    "I spend quite a bit of money on music and related items.",
    "I sometimes feel chills when I hear a melody that I like.",
    "Music comforts me.",
    "When I hear a tune I like a lot I can't help tapping or moving to its beat.",
]

# ─────────────────────────────────────────────
# GOLDSMITHS MUSICAL SOPHISTICATION INDEX (Gold-MSI)
# 31 agreement items (7-point) + 7 training/engagement items
# ─────────────────────────────────────────────

GOLD_MSI_SCALE = ["Completely disagree", "Strongly disagree", "Disagree",
                  "Neither agree nor disagree", "Agree", "Strongly agree", "Completely agree"]

GOLD_MSI_ITEMS = [
    "I spend a lot of my free time doing music-related activities.",
    "I sometimes choose music that can trigger shivers down my spine.",
    "I enjoy writing about music, for example on blogs and forums.",
    "If somebody starts singing a song I don't know, I can usually join in.",
    "I am able to judge whether someone is a good singer or not.",
    "I usually know when I'm hearing a song for the first time.",
    "I can sing or play music from memory.",
    "I'm intrigued by musical styles I'm not familiar with and want to find out more.",
    "Pieces of music rarely evoke emotions for me.",
    "I am able to hit the right notes when I sing along with a recording.",
    "I find it difficult to spot mistakes in a performance of a song even if I know the tune.",
    "I can compare and discuss differences between two performances or versions of the same piece of music.",
    "I have trouble recognizing a familiar song when played in a different way or by a different performer.",
    "I have never been complimented for my talents as a musical performer.",
    "I often read or search the internet for things related to music.",
    "I often pick certain music to motivate or excite me.",
    "I am not able to sing in harmony when somebody is singing a familiar tune.",
    "I can tell when people sing or play out of time with the beat.",
    "I am able to identify what is special about a given musical piece.",
    "I am able to talk about the emotions that a piece of music evokes for me.",
    "I don't spend much of my disposable income on music.",
    "I can tell when people sing or play out of tune.",
    "When I sing, I have no idea whether I'm in tune or not.",
    "Music is kind of an addiction for me - I couldn't live without it.",
    "I don't like singing in public because I'm afraid that I would sing wrong notes.",
    "When I hear a piece of music I can usually identify its genre.",
    "I would not consider myself a musician.",
    "I keep track of new music that I come across (e.g. new artists or recordings).",
    "After hearing a new song two or three times, I can usually sing it by myself.",
    "I only need to hear a new tune once and I can sing it back hours later.",
    "Music can evoke my memories of past people and places.",
]

# (question, response options) — standard Gold-MSI options
GOLD_MSI_TRAINING_QUESTIONS = [
    ("I engaged in regular, daily practice of a musical instrument (including voice) for ___ years.",
     ["0", "1", "2", "3", "4-5", "6-9", "10 or more"]),
    ("At the peak of my interest, I practiced ___ hours per day on my primary instrument.",
     ["0", "0.5", "1", "1.5", "2", "3-4", "5 or more"]),
    ("I have attended ___ live music events as an audience member in the past twelve months.",
     ["0", "1", "2", "3", "4-6", "7-10", "11 or more"]),
    ("I have had formal training in music theory for ___ years.",
     ["0", "0.5", "1", "2", "3", "4-6", "7 or more"]),
    ("I have had ___ years of formal training on a musical instrument (including voice) during my lifetime.",
     ["0", "0.5", "1", "2", "3-5", "6-9", "10 or more"]),
    ("I can play ___ musical instruments.",
     ["0", "1", "2", "3", "4", "5", "6 or more"]),
    ("I listen attentively to music for ___ per day.",
     ["0-15 min", "15-30 min", "30-60 min", "60-90 min", "2 hrs", "2-3 hrs", "4 hrs or more"]),
]
