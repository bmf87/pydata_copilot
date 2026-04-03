from cgitb import reset
import re
import streamlit as st
from pydc.util import constants
from pydc.session.pydc_session import PydcSessionWrapper


EDIT_KEYWORDS = [
    "amend", "add", "remove", "modify", "change", "update", "tweak", "adjust", "edit", "now",
    "switch", "flip", "swap", "keep", "same plot", "also", "as before", "as originally instructed"
]

NEW_KEYWORDS = [
    "create", "start", "new plot", "new chart", "new figure", "new graph", "new table", "new dataframe",
    "start over", "from scratch", "completely different", "ignore previous", "reset", 
    "different plot", "different graph", "different chart", "different figure", "different table"
]

def classify_intent(user_text: str, pydc: PydcSessionWrapper) -> str:
    text = user_text.lower()

    # Strong signals for starting over
    text_cf = user_text.casefold()
    if any(phrase.casefold() in text_cf for phrase in NEW_KEYWORDS):
        return constants.NEW_USER_INTENT

    # Strong signals for incremental edit
    if any(phrase.casefold() in text_cf for phrase in EDIT_KEYWORDS):
        return constants.EDIT_USER_INTENT

    # Default/Naive Heuristic: if there's a table or plot in session, default to edit
    return constants.EDIT_USER_INTENT if pydc.table is not None or pydc.figure is not None else constants.NEW_USER_INTENT