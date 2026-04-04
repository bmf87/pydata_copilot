import numpy as np
import pandas as pd
import json, re
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import seaborn as sns
from typing import Any, Dict, Literal, Optional, Tuple
import streamlit as st
import pydc.util.constants as constants

log = st.logger.get_logger(__name__)


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    # Remove single leading fence line like ```json or ```
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    # Remove trailing fence
    text = re.sub(r'\s*```$', '', text)
    return text.strip()

def _normalize_code_field(raw: str) -> str:
    """
    Normalize the value of the "code" field in an LLM JSON-like response to prepare it for json.loads():
    - Allow raw newlines in the code string and convert them to '\n'.
    - Escape any inner double quotes to make valid JSON.
    """
    # LLM response may contain markdown fences, e.g. ```json ... ```
    #raw = _strip_markdown_fence(raw)
    # Match: "code": "<anything, including newlines>"
    pattern = r'"code"\s*:\s*"((?:[^"\\]|\\.|[\r\n])*)"'

    def repl(m: re.Match) -> str:
        # Original inner contents of the "code" string
        code_raw = m.group(1)

        # 1) Change raw literal line endings to escaped \\n
        # We DO NOT double-escape \ or " here, because if they matched 
        # inside the string they are already valid JSON escapes!
        code_fixed = (
            code_raw
            .replace('\r\n', '\\n')
            .replace('\r', '\\n')
            .replace('\n', '\\n')
        )

        # Rebuild the full "code": "..." pair
        return f'"code": "{code_fixed}"'

    return re.sub(pattern, repl, raw, flags=re.DOTALL)

def _sanitize_code(code: str) -> str:
    """
    Remove any line with plt.show, .show(, st.pyplot, display(
    These patterns are common in training data, so “plot” → “plt.show()” is a strong default pattern.
    Prompting alone was not always enough to prevent the model from generating these patterns, since open-source models 
    (especially small ones) don’t strictly enforce negative constraints across all generations.
    """
    lines = code.splitlines()
    cleaned = [
        ln for ln in lines
        if "plt.show" not in ln and ".show(" not in ln and "st.pyplot" not in ln and "display(" not in ln
    ]
    code = "\n".join(cleaned)
    # Workaround: v0.2.62 GPU tokenization bug prepends 'G' to short identifiers like 'df' → 'Gdf'
    code = re.sub(r'\bGdf\b', 'df', code)
    return code

def parse_llm_response(raw_response: str) -> Dict[str, Any]:
    """
    Parse the raw response from the LLM and return a dictionary with the following keys:
        - type: "table" or "figure"
        - code: "<python code>"
        - return: "result_df" or "result_fig"

        result = {
            "type": "table",
            "code": "result_df = df.head(5)",
            "return": "result_df",
            "errors": ""
        }
    """
    result = {}
    errors = None 
    raw_response = _strip_markdown_fence(raw_response)
    
    try:
        # FAST PATH: IF valid JSON (with correctly escaped \" quotes) 
        # then just let the native json library decode it cleanly.
        result = json.loads(raw_response)
    except json.JSONDecodeError:
        # FALLBACK: The LLM likely added raw newlines inside the string! 
        # Run our targeted normalizer on it and re-attempt.
        log.warn("Standard JSON parse failed, attempting code block raw newline normalization...")
        normalized_response = _normalize_code_field(raw_response)
        log.debug(f"[normalized_response]: {normalized_response}")
        
        try:
            result = json.loads(normalized_response)
        except json.JSONDecodeError as e:
            # handle bad LLM output
            result["errors"] = f"LLM returned invalid JSON: {e}"
            log.error(result["errors"])

    # internal result: dict
    res_type = result.get("type", "")
    ret_name = result.get("return", "")
    code_str = result.get("code", "").replace('\\n', '\n')
    errors = result.get("errors", "")
    ret_name = constants.RESULT_DF_NAME
        
    # Remove any .show() calls from the code string
    code_str = _sanitize_code(code_str)
    
    return {
        "type": res_type,
        "code": code_str,
        "return": ret_name,
        "errors": errors,
    }


def run_llm_code(code: str, df: pd.DataFrame) :
    log.debug(f"[run_llm_code] - code: {code}")
    log.debug(f"[run_llm_code] - df: {df}")
    # Globals the code is allowed to see
    global_ns = {
        "__builtins__": __builtins__,  # or a pruned version if you want tighter sandboxing
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
        "df": df,
    }
    local_ns = {}
    try:
        exec(code, global_ns, local_ns)  # variables end up in local_ns
    except Exception as e:
        log.error(f"Error executing LLM code: {e}")
        # Safely insert the error into the namespace so classify_code_result can see it
        local_ns["__error__"] = f"{type(e).__name__}: {str(e)}"
        
    return local_ns


def is_displayable_plot(obj) -> bool:
    SEABORN_GRID_TYPES = (sns.axisgrid.FacetGrid,
                          sns.axisgrid.PairGrid,
                          sns.axisgrid.JointGrid)
    return (
        isinstance(obj, Figure) or
        isinstance(obj, Axes) or
        isinstance(obj, SEABORN_GRID_TYPES)
    )


ResultType = Literal["table", "figure", "unknown"]

def classify_code_result(result_type: str, ns: Dict[str, Any]) -> Tuple[ResultType, Optional[pd.DataFrame], Optional[plt.Figure], Dict[str, Any]]:
    """
    Perform LLM code execution result classification. Inspect the exec namespace 
   
    Returns:
        Tuple(result_type, table, figure, errors)
    """
    errors: Dict[str, Any] = {}
    log.debug(f"[classify_code_result] - result_type: {result_type}")
    log.debug(f"[classify_code_result] - ns keys: {list(ns.keys())}")  
    
    if "__error__" in ns:
        errors["execution"] = f"The generated code encountered an error during execution: <b>{ns['__error__']}</b>. Please modify your prompt and try again."
        return constants.RESULT_TYPE_UNKNOWN, None, None, errors
        
    if not ns:
        errors["empty_namespace"] = "The generated code did not produce any variables or output. Please modify your prompt and try again."
        return constants.RESULT_TYPE_UNKNOWN, None, None, errors

    # Df/Table case
    if result_type == constants.RESULT_TYPE_TABLE:
        if constants.RESULT_DF_NAME not in ns:
            errors["missing"] = "result_df not defined in executed code"
            return constants.RESULT_TYPE_UNKNOWN, None, None, errors

        data = ns[constants.RESULT_DF_NAME]
        if isinstance(data, pd.DataFrame) or isinstance(data, pd.Series):
            return constants.RESULT_TYPE_TABLE, data, None, errors
        else:
            errors["bad_data_type"] = "result['return'] - not a pandas DataFrame for type='table'"
            return constants.RESULT_TYPE_UNKNOWN, None, None, errors

    # Figure case
    if result_type == constants.RESULT_TYPE_FIGURE:
        if constants.RESULT_FIG_NAME not in ns:
            errors["missing"] = "result_fig not defined in executed code"
            return constants.RESULT_TYPE_UNKNOWN, None, None, errors

        fig = ns[constants.RESULT_FIG_NAME]
        if is_displayable_plot(fig):
            return constants.RESULT_TYPE_FIGURE, None, fig, errors
        else:
            errors["bad_data_type"] = "result['return'] - not a matplotlib Figure, Axes, or Seaborn Grid for type='figure'"
            return constants.RESULT_TYPE_UNKNOWN, None, None, errors

    errors["unknown_type"] = f"Unsupported result['return']: {result_type!r}"
    return constants.RESULT_TYPE_UNKNOWN, None, None, errors
