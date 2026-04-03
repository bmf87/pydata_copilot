import os, logging, time
from pathlib import Path
import base64
import streamlit as st
import streamlit.components.v1 as components
from streamlit.runtime.scriptrunner import get_script_run_ctx
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pydc.dataset.dataset_handler import get_dataset_handler
from pydc.session.pydc_session import PydcSessionWrapper
from pydc.session import memory_store
import pydc.util.constants as constants
import pydc.util.app_config as app_config
import pydc.llm.inference as inference
import pydc.code.pydc_exec as pydc_exec
from pydc.interaction.turn import (
    get_relevant_memories, classify_intent, build_coding_prompt, 
    call_llm, execute_code
)


#
# App Configuration
#
simulate = app_config.get("simulate", True)
model_name = app_config.get("model_name", "Qwen2.5 Coder 7B")
memory_store_size = app_config.get("memory_store_size", 3)
memory_store_hits = app_config.get("memory_store_hits", 3)
log = st.logger.get_logger(__name__)
# Initialize Pydc Session Wrapper once per run
pydc = PydcSessionWrapper.from_session()
st.caption(f"*Powered by {model_name}*")
st.set_page_config(
    page_title=constants.PAGE_TITLE,
    page_icon=constants.PAGE_ICON,
    layout="wide",
)

# PreLoad (warm LLM on startup
llm = inference.load_inference_model()

# Load custom CSS
with open("ui/styles/chat_input.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def init_images():
    global logo_img_b64
    pydc.user_avatar = constants.IMAGE_LKP["user_avatar"]
    pydc.assistant_avatar = constants.IMAGE_LKP["assistant_avatar"]
    pydc.python_logo = constants.IMAGE_LKP["python_logo"]
    # Encode image in base64
    logo_img_bytes = Path(pydc.python_logo).read_bytes()
    logo_img_b64 = base64.b64encode(logo_img_bytes).decode("utf-8")

def init_session(dataset_handler):
    """Reset the entire session state."""
    log.debug("[SESSION] - Initializing new session with dataset: %s", dataset_handler.file_name)
    pydc.reset(dataset_handler)

def update_df_row_slider(df_row_slider):
    log.debug("In update_df_row_slider: Updating df_row_slider to %s", df_row_slider)
    pydc.df_row_slider = df_row_slider

def get_session_id():
    session_id = get_script_run_ctx().session_id
    return session_id

# ------ Begin Layout ------

# Sidebar (File Upload & Dataset Info)
with st.sidebar:
    st.title("🗂️ Dataset Settings")
    uploaded_file = st.file_uploader(
        "Upload a dataset", 
        type=["csv", "xlsx", "xls", "parquet"]
    )
    
    if uploaded_file is not None:
        # Check if it's a new file upload
        if pydc.file_name != uploaded_file.name:
            log.debug("New file uploaded: %s", uploaded_file.name)
            # Get dataset using custom handler
            try:
                # Streamlit file.type contains mime-type which our handler expects
                dataset_handler = get_dataset_handler(uploaded_file.type)
                df = dataset_handler.handle_upload(uploaded_file)
                init_session(dataset_handler)    
                
                # Add dataset summary to In-memory store
                memory_store.store_dataset_summary(
                    schema=dataset_handler.get_schema(),
                    columns=dataset_handler.get_columns(),
                    file_name=uploaded_file.name
                )
                
                st.success(f"Successfully loaded: {uploaded_file.name}")
            except Exception as e:
                # If MIME lookup fails, try fallback using file extension
                try:
                    ext = uploaded_file.name.split('.')[-1].lower()
                    if ext == 'csv':
                        ext_type = 'text/csv'
                    elif ext == 'xlsx':
                        ext_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    elif ext == 'xls':
                        ext_type = 'application/vnd.ms-excel'
                    elif ext == 'parquet':
                        ext_type = 'application/octet-stream'
                    else:
                        ext_type = 'unknown'
                        
                    dataset_handler = get_dataset_handler(ext_type)
                    df = dataset_handler.handle_upload(uploaded_file)
                    init_session(dataset_handler)  
                    
                    # Store dataset summary in memory
                    memory_store.store_dataset_summary(
                        schema=dataset_handler.get_schema(),
                        columns=dataset_handler.get_columns(),
                        file_name=uploaded_file.name
                    )
                    
                    st.success(f"Successfully loaded: {uploaded_file.name} (via extension fallback)")
                except Exception as error:
                    st.error(f"Error loading file: {str(error)}")

    # Display dataset info if loaded
    if pydc.df is not None:
        st.write("---")
        st.write("### Dataset Specifications")
        st.write(f"**Rows:** {pydc.df.shape[0]:,}")
        st.write(f"**Columns:** {pydc.df.shape[1]:,}")

# ---- Main Interface ----
init_images()
# Header: Python logo with title
st.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 1rem;">
        <img src="data:image/png;base64,{logo_img_b64}" width="35">
        <h1>{constants.PAGE_TITLE}</h1>
    </div>
    """,
    unsafe_allow_html=True
)

if pydc.df is None:
    st.info("👋 Welcome! Please upload a dataset in the sidebar to begin.")
    help_text = """
    Python Data Copilot allows you to enter natural language queries against uploaded datasets.
    Based on your queries, it will:

    - Generate Python code and run it on a Pandas dataframe created from your uploaded dataset.
    - Use an LLM, *'aligned'* to a curated data analysis preference dataset, to generate the code.
    
    *:small[Created by: Brett Favro]*

    """

    with st.expander("ℹ️ *Using PyData Copilot*"):
        st.write(help_text)

# Chat History Area
chat_container = st.container()
with chat_container:
    for message in pydc.messages:
        with st.chat_message(message["role"], avatar=message["avatar"]):
            st.markdown(message["content"])

# Chat Input Area
prompt = st.chat_input(f"Ask a question about the data in {pydc.file_name}...")

with open("ui/styles/prompt_hints.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

hint_html = """
<div class="chat-hint-wrapper">
    <details class="chat-hint-details">
        <summary class="chat-hint-summary">💡 Prompting Hints</summary>
        <div class="chat-hint-content">
            <b>How to get the best results:</b><br>
            • <b>Be specific:</b> While you can use terms like 'price' for 'housing_price', it is best to state exact column names in your prompts.<br>
            • <b>Ask for visualizations:</b> "Create a bar chart of X vs Y" or "Create a correlation heatmap" or "Create a histogram of X".<br>
            • <b>Data transformations:</b> "Create a table that filters the data where sales > 1,000,000".<br>
            • <b>Changing existing output:</b> Use words that denote change/update/adjustments, like "<i>'Add'</i> quartiles to the plot" or "<i>'Remove'</i> rows where country == US".<br>
            • <b>Starting a new analysis:</b> Use words that denote new/starting over/resetting an analysis, such as "<i>'Start'</i> a new analysis by creating a histogram of area" or "<i>'Clear'</i> the current analysis and ..." 
                or "<i>'Create'</i> a scatter plot showing sales per quarter with sales on the y-axis".
        </div>
    </details>
</div>
"""
st.markdown(hint_html, unsafe_allow_html=True)
# Moves prompt hint div into chat_input DOM
js_code = """
<script>
    const moveHint = () => {
        const parentDoc = window.parent ? window.parent.document : document;
        const hint = parentDoc.querySelector('.chat-hint-wrapper');
        const chatInput = parentDoc.querySelector('[data-testid="stChatInput"]');
        if (hint && chatInput && hint.parentElement !== chatInput) {
            chatInput.style.position = 'relative'; 
            chatInput.appendChild(hint);
        }
    };
    const observer = new MutationObserver(moveHint);
    observer.observe(window.parent ? window.parent.document.body : document.body, { childList: true, subtree: true });
    moveHint();
</script>
"""
components.html(js_code, height=0)


if prompt:
    # No df uploaded
    if pydc.df is None:
        st.error("Please upload a dataset to begin.")
    else:
        # User Message
        pydc.messages.append({"role": "user", "avatar": pydc.user_avatar, "content": prompt})
        with chat_container:
            with st.chat_message("user", avatar=pydc.user_avatar):
                st.markdown(prompt)

        # Assistant Message
        response_text = f"""After analyzing your query: *'{prompt}'*, I've generated Python code in the Output Workspace below, *please review it*"""
        pydc.messages.append({"role": "assistant", "avatar": pydc.assistant_avatar, "content": response_text})      
    
        with chat_container:
            with st.chat_message("assistant", avatar=pydc.assistant_avatar):
                if simulate:
                    with st.spinner("Analyzing data..."):
                        time.sleep(2) # Simulate backend LLM parsing and code gen
                        
                    generated_code = f"# Q: {prompt}\nimport pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\n\n# Provide overview metrics\nprint(df.head())\nprint(df.describe())\n\n# Generate Correlation Matrix Plot\nnumeric_df = df.select_dtypes(include='number')\nif len(numeric_df.columns) > 1:\n    plt.figure(figsize=(10, 8))\n    sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', fmt='.2f')\n    plt.title('Correlation Analysis')\n    plt.tight_layout()\n    plt.show()\n"
                    pydc.generated_code = generated_code
                    st.markdown(response_text)
                else:
                    st.markdown(
                        """
                        <style>
                        /* Color the filled part of all progress bars */
                        .stProgress > div > div > div > div {
                            background-color: #055E17;  /* or a gradient, etc. */
                            /* background-image: linear-gradient(to right, #99ff99, #00ccff); */
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )
                    
                    steps = [
                        ("Retrieving memories…", get_relevant_memories),
                        ("Classifying intent…", classify_intent),
                        ("Building prompt…", build_coding_prompt),
                        (f"Preparing to call {model_name}…", call_llm),
                        ("Executing generated code…", execute_code),
                    ]
                        
                    ctx = {"prompt": prompt, "pydc": pydc, "memory_store_size": memory_store_size, "memory_store_hits": memory_store_hits, "model_name": model_name}
                    placeholder = st.empty()  # container for status UI
                    with placeholder.container():
                        progress = st.progress(0)
                        status = st.empty()
                        total_steps = (len(steps) + constants.LLM_SUB_STEPS) # add micro-steps in call_llm
                        ctx["progress"] = progress
                        ctx["status"] = status
                        ctx["total_steps"] = total_steps

                        for i, (label, fn) in enumerate(steps, start=1):
                            ctx["step_idx"] = i
                            status.text(label)
                            ctx = fn(ctx)
                            progress.progress(int(i / total_steps * 100))

                        time.sleep(1)
                        status.text("Done!")
                        
                    placeholder.empty()
                    st.markdown(response_text)
                    
                    result_type, table, fig, code_errors = ctx.get("code_results")

                    #pydc.generated_code = ctx.results.get("code", "")

                    if result_type == constants.RESULT_TYPE_TABLE:
                        log.debug(f"Table result: {table}")
                        pydc.result_type = constants.RESULT_TYPE_TABLE
                        pydc.table = table  # show in agg / table tab
                        pydc.figure = None
                    elif result_type == constants.RESULT_TYPE_FIGURE:
                        log.debug(f"Figure result: {fig}")
                        pydc.result_type = constants.RESULT_TYPE_FIGURE
                        pydc.figure = fig  # show in viz tab
                        pydc.table = table # show in agg / table tab
                    else:    # unknown result type
                       log.debug(f"Unknown result type: {result_type}")
                       pydc.result_type = constants.RESULT_TYPE_UNKNOWN
                       pydc.table = None
                       pydc.figure = None
                      
        # State Update for UI Expansion
        pydc.has_asked_question = True
        #st.rerun()

# 3. Dynamic Expandable Workspace area
if pydc.df is not None and pydc.has_asked_question:
    st.markdown("---")
    
    # Toggle to unhide the code tab
    col1, col2 = st.columns([8, 2])
    with col1:
        st.subheader("📊 Output Workspace")
    with col2:
        #st.session_state.show_code = st.toggle("Unhide Code Tab", value=st.session_state.show_code)
        pydc.show_code = st.toggle("Unhide Code Tab", value=pydc.show_code)
        
    tabs_list = [constants.DATA_VIEW_TAB, constants.VISUALIZATIONS_TAB]
    if pydc.show_code:
        tabs_list.append(constants.CODE_SNIPPET_TAB)
        
    # Set which tab should be active based on result_type
    if pydc.result_type == constants.RESULT_TYPE_TABLE:
        active_tab_name = constants.DATA_VIEW_TAB
    elif pydc.result_type == constants.RESULT_TYPE_FIGURE:
        active_tab_name = constants.VISUALIZATIONS_TAB
    else: # default
        active_tab_name = constants.DATA_VIEW_TAB

    log.debug(f"Active tab name: {active_tab_name}")
    # Bring desired active tab to the front.
    if active_tab_name in tabs_list:
        tabs_list.remove(active_tab_name)
        tabs_list.insert(0, active_tab_name)
        
    tabs = st.tabs(tabs_list)
    
    # Store explicit references to the generated tabs
    tab_data_view = tabs[tabs_list.index(constants.DATA_VIEW_TAB)]
    tab_visualizations = tabs[tabs_list.index(constants.VISUALIZATIONS_TAB)]
    if pydc.show_code:
        tab_code = tabs[tabs_list.index(constants.CODE_SNIPPET_TAB)]
            
    # TAB 1: Tabular Data View 
    with tab_data_view:
        
        log.debug("df_row_slider initialized to %s", pydc.df_row_slider)
        if pydc.table is not None and pydc.table.shape[0]>0:    
            st.slider("Number of rows to display", 
                min_value=1, 
                max_value=pydc.table.shape[0],
                key="df_row_slider",
                on_change=update_df_row_slider(pydc.df_row_slider 
                                        if pydc.df_row_slider <= pydc.table.shape[0]
                                        else 2)
        )
       
        # Fetch the slider value directly from session state
        rows = pydc.df_row_slider
                
        if simulate: # Simulate generated table execution based on mocked code 
            str_df_rows = pydc.dataset_handler.get_head(rows).astype(str)
            str_df_stats = pydc.dataset_handler.get_descriptive_statistics(include='number').astype(str) 
        else: # Display LLM generated table
            if pydc.table is not None: # table/result_df
                str_df_rows = pydc.table.head(rows).astype(str)
                str_df_stats = pydc.table.describe().astype(str) 
            else:                     # figure/result_fig
                str_df_rows = pydc.df.head(rows).astype(str)
                str_df_stats = pydc.df.describe().astype(str) 
        
            st.markdown(f"**Data Head (Top {rows} Rows)**")
            st.dataframe(str_df_rows, width='stretch')
        
            st.markdown("**Descriptive Statistics (Aggregations)**")
            st.dataframe(str_df_stats, width='stretch')
        
    # TAB 2: Data Visualizations
    with tab_visualizations:
        st.markdown("**Visual Display (Matplotlib/Seaborn)**")
        
        if simulate: # Simulate generated plot execution based on mocked code 
            numeric_cols = pydc.dataset_handler.df.select_dtypes(include='number').columns
            st_fig, st_ax = plt.subplots(figsize=(10, 8))
            if len(numeric_cols) > 1:
                sns.heatmap(pydc.df[numeric_cols].corr(), annot=True, cmap='coolwarm', fmt='.2f', ax=st_ax)
                st_ax.set_title("Correlation Analysis of Numeric Features")
            else:
                st_ax.text(0.5, 0.5, "Not enough numeric data for default correlation plot.", ha='center', va='center')
                st_ax.axis('off')
        else: # Display LLM generated figure
            # if 'figure' in pydc, use it, otherwise display message "No Figure Generated."
            if pydc.figure is not None:
                st_fig = pydc.figure
                st_ax = st_fig.axes[0]
            else:
                st_fig, st_ax = plt.subplots(figsize=(10, 8))
                st_ax.text(0.5, 0.5, "No Figure Generated.", ha='center', va='center')
                st_ax.axis('off')
        
        st.pyplot(st_fig)
        
    # Tab 3: Code Content (Hidden by Default)
    if pydc.show_code:
        with tab_code:
            st.markdown("PyData Copilot Generated Code:")

            # Display Code in clean format with scrolling native to st.code
            st.code(pydc.generated_code, language="python", line_numbers=True)
            
            # Permit explicit saving to filesystem or copy
            st.download_button(
                label="📥 Save Code to File",
                data=pydc.generated_code,
                file_name="pydc_generated_code.py",
                mime="text/x-python"
            )
  