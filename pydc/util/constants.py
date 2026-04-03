

PAGE_TITLE = "PyData Copilot"
APP_CONFIG_PATH = ".streamlit/app.toml"
ROW_SLIDER_DEFAULT = 3

# Image paths
PAGE_ICON = "ui/images/pydata_copilot.png"
ASSISTANT_AVATAR_PATH = "ui/images/pydata_copilot_avatar.png"
USER_AVATAR_PATH = "ui/images/user_avatar.png"
PYTHON_LOGO_PATH = "ui/images/python_logo.png"

IMAGE_LKP = ({
    "assistant_avatar": ASSISTANT_AVATAR_PATH,
    "user_avatar": USER_AVATAR_PATH,
    "python_logo": PYTHON_LOGO_PATH
})

# Tabs
DATA_VIEW_TAB = "Data View"
VISUALIZATIONS_TAB = "Visualizations"
CODE_SNIPPET_TAB = "Code Snippet"

NEW_USER_INTENT = "new"
EDIT_USER_INTENT = "edit"

# Memory Store Constants
MEMORY_STORE_KEY = "memory_store"
MEMORY_TYPE_DATASET_SUMMARY = "dataset_summary"
MEMORY_TYPE_PRIOR_PROMPT = "prior_prompt"
MEMORY_KEY = "memory"
MEMORY_TS = "memory_ts"
AGENT_CODE = "agent_code"
USER_PROMPT = "user_prompt"

# LLM Constants
LLM_SUB_STEPS = 5

# Result Type Constants
RESULT_TYPE_TABLE = "table"
RESULT_TYPE_FIGURE = "figure"
RESULT_TYPE_UNKNOWN = "unknown"

RESULT_DF_NAME = "result_df"
RESULT_FIG_NAME = "result_fig"

# Inference Model Constants
INFERENCE_REPO_ID_1_5B = "bfavro73/qwen2.5-coder-1.5b-pandas-dpo-aligned"
INFERENCE_MODEL_1_5B = "qwen2.5-coder-1.5b-pandas-dpo-aligned-q4_k_m.gguf"

INFERENCE_REPO_ID_7B = "bfavro73/qwen2.5-coder-7b-pandas-dpo-aligned"
INFERENCE_MODEL_7B = "qwen2.5-coder-7b-pandas-dpo-aligned-q4_k_m.gguf"

# Embedding Model Constants
EMBEDDING_REPO_ID = "nomic-ai/nomic-embed-text-v1.5-GGUF"
EMBEDDING_MODEL = "nomic-embed-text-v1.5.Q4_K_M.gguf"