import streamlit as st
from typing import Any, Dict, Literal, Optional, Tuple
from st_flexible_callout_elements import flexible_callout, flexible_error
from pydc.session import memory_store
from pydc.interaction import user_intent
from pydc.session.pydc_session import PydcSessionWrapper
import pydc.llm.inference as inference
import pydc.llm.prompt_utils as prompt_utils
import pydc.code.pydc_exec as pydc_exec
import pydc.util.constants as constants

log = st.logger.get_logger(__name__)

def get_relevant_memories(ctx: Dict) -> Dict:
    """
    Retrieves relevant memories from the memory store based on the user's prompt.
    
    Args:
        ctx (Dict): The context dictionary containing the user's prompt and memory store configuration.
        
    Returns:
        Dict: The context dictionary with the retrieved memories added.
    """
    prompt, memory_store_size, memory_store_hits = (ctx[k] for k in (
        "prompt", "memory_store_size", "memory_store_hits")
    )
    # Retrieve prior session-based memories
    memories = memory_store.get_relevant_memories(prompt, memory_store_hits, memory_store_size)
    log.info(f"Retrieved memories:\nMemory Store Hits: {len(memories)} of {memory_store_hits}")
    log.debug(f"\nMemories:\n{memories}")
    ctx["memories"] = memories
    return ctx

def classify_intent(ctx: Dict) -> Dict:
    prompt = ctx["prompt"]
    pydc: PydcSessionWrapper = ctx["pydc"]
    intent = user_intent.classify_intent(prompt, pydc)
    log.info(f"Inferred User Intent: `{intent}`")
    ctx["user_intent"] = intent
    return ctx

def build_coding_prompt(ctx: Dict) -> Dict:
    intent = ctx["user_intent"]
    prompt = ctx["prompt"]
    pydc: PydcSessionWrapper = ctx["pydc"]
    memories = ctx["memories"]
    if intent == constants.EDIT_USER_INTENT:
        llm_prompt = prompt_utils.build_editing_code_prompt(prompt, pydc, memories)
        log.debug(f"[Constructed Prompt] - Editing code prompt:\n{llm_prompt}")
    else:
        llm_prompt = prompt_utils.build_new_coding_prompt(prompt, pydc, memories)
        log.debug(f"[Constructed Prompt] - New code prompt:\n{llm_prompt}")
    ctx["llm_prompt"] = llm_prompt
    return ctx
    
def call_llm(ctx: Dict) -> Dict:
    sub_steps = 5
    pydc: PydcSessionWrapper = ctx["pydc"]
    llm_prompt, progress, status, step_idx, total_steps, model_name = (ctx[k] for k in (
        "llm_prompt", "progress", "status", "step_idx", "total_steps", "model_name")
    )
    
    overall_total_steps = total_steps + sub_steps
     # substep 1
    status.text(f"Preparing prompt...")
    progress.progress(int(((step_idx + 1) / overall_total_steps) * 100))
   
    dot_states = ["", ".", "..", "...", "....", "....."]
        
    # longest cost --> substep 2
    status.text(f"Calling {model_name}...")
    progress.progress(int(((step_idx + 2) / overall_total_steps) * 100))
    
    # LLM raw response --> generated_code
    chunks = inference.chat_stream(llm_prompt)
    full_text, chunk_ctr, dot_idx = [], 1, 0
    dots = dot_states[dot_idx]
    for token in chunks:
        if chunk_ctr % 5 == 0:
            dots = dot_states[dot_idx]
            dot_idx = (dot_idx + 1) % len(dot_states)
        full_text.append(token)
        # substep 3
        status.text(f"Receiving tokens from {model_name}{dots}")
        if chunk_ctr == 1:
            progress.progress(int(((step_idx + 3) / overall_total_steps) * 100))
        chunk_ctr += 1

    raw_response = "".join(full_text)
    log.debug(f"[RAW LLM RESPONSE]:\n{raw_response}")  # temporary diagnostic
    #raw_response = inference.chat_once(llm_prompt)
    status.text(f"Parsing {model_name} response...")
    progress.progress(int(((step_idx + 4) / overall_total_steps) * 100))

    # returns dict with keys: type, code, return, errors
    results = pydc_exec.parse_llm_response(raw_response)
    pydc.errors = results.get("errors", "")
    pydc.result_type = results.get("type", "")
    pydc.generated_code = results.get("code", "")
    ctx["results"] = results
    status.text(f"Returning {model_name} response...")
    progress.progress(int(((step_idx + 5) / overall_total_steps) * 100))

    return ctx

def _show_errors(title: str, errors: str):  
    log.error(f"[LLM ERROR] - {errors}")
    flexible_error(
        message=f"{title}: {errors}<br><br>Refine your prompt and try again!",
        container=st,
        font_size=16,
        alignment="left", 
    )
    st.stop()

def execute_code(ctx: Dict) -> Dict:
    ResultType = Literal["table", "figure", "unknown"]
    result: Tuple[ResultType, Optional[pd.DataFrame], Optional[plt.Figure], Dict[str, Any]]
    pydc: PydcSessionWrapper = ctx["pydc"]
    results = ctx["results"]
    prompt = ctx["prompt"]
    # Show JSON parsing issues
    if pydc.errors:
        log.debug(f"LLM Response Error: {pydc.errors}")
        _show_errors("LLM Response Parsing Error: ", pydc.errors)
    
    # Execute LLM-generated code and classify result
    if not pydc.errors and pydc.generated_code:
        ns = pydc_exec.run_llm_code(pydc.generated_code, pydc.df)
        result_type, table, fig, code_errors = pydc_exec.classify_code_result(pydc.result_type, ns)
        log.debug(f"Result type: {result_type}")
        log.debug(f"Generated code:\n{pydc.generated_code}")
        ctx["code_results"] = (result_type, table, fig, code_errors)

        output_summary = f"Result Type: {result_type}."
        if code_errors:
            output_summary += f" Code Execution Errors: {code_errors}"
            pydc.errors = code_errors
            _show_errors("LLM Code Execution Error: ", code_errors) 
       
        # Add interaction/turn to In-memory store
        memory_store.store_exchange(prompt, pydc.generated_code, output_summary)
    
    return ctx