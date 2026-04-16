import csv, re, yaml
import streamlit as st
from pydc.session.pydc_session import PydcSessionWrapper
from pydc.util.constants import (
    MEMORY_KEY, MEMORY_TS, AGENT_CODE, USER_PROMPT
)

log = st.logger.get_logger(__name__)

def _get_df_info(pydc: PydcSessionWrapper, rows: int = 3) -> str:
    # Extract df schema and data sample
    #df_info = f"Dataframe Name: {pydc.file_name}\n\n"
    df_info = f"Columns and Data Types:\n{pydc.df.dtypes.to_string()}\n\n"
    df_info += f"Sample Data (first {rows} rows):\n{pydc.df.head(rows).to_csv(index=False)}\n"
    return df_info

def _get_critical_requirements()-> str:
  critical_requirements = r'''
   <CRITICAL_REQUIREMENTS>
    - A pandas DataFrame named df is ALREADY loaded in memory.
    - df already contains all the data the user is asking about.
    - You MUST NOT load data from disk or network.
    - When generating your response, you MUST follow these steps:
      1.You MUST obey the <USER_PROMPT> section
        - If anything conflicts with <USER_PROMPT>, you MUST follow <USER_PROMPT>.
      2.You MUST obey the <RULES> section.
        - You MUST NOT violate any rule in <RULES> under any circumstance.
      3.You MUST read the <MEMORIES> section before answering.
        - If <MEMORIES> contain details relevant to the current user request, you MUST use those details in your answer.
        - When applicable, you MUST prefer concrete details in <MEMORIES> over generic assumptions.
        - If <MEMORIES> conflict with the <USER_PROMPT>, you MUST follow <USER_PROMPT>.
      4.You MUST obey the <DISPLAY_RULES> and <FORMAT_REQUIREMENTS> sections.
        - These are strict output constraints and you MUST follow them exactly.
      5.You SHOULD use the <FINAL_CHECKLIST> section to verify your output before responding.
        - Before you respond, you SHOULD confirm that your answer satisfies all items in <FINAL_CHECKLIST>

      <DISPLAY_RULES>
        - You MUST NOT call any display function: plt.show(), plt.show(fig), plt.figure().show(),
          st.pyplot(), display(), or similar.
        - The final figure MUST be returned only via: result_fig = plt.gcf().
        - Before sending your answer, you MUST check your code string:
          - It MUST NOT contain "plt.show" or "show(" in any form.
          - If it does, remove those calls and fix the code before responding.
      </DISPLAY_RULES>

      <FORMAT_REQUIREMENTS>
       - Respond with a SINGLE JSON object only. You must respond with a SINGLE valid JSON object, and nothing else.
        - Do NOT include any Markdown, backticks, comments, or explanatory text.
        - The JSON object MUST contain ALL of these top-level keys:
          - "type"
          - "code"
          - "return"
       - You MUST NOT omit any of these top-level keys; You MUST NOT add extra top-level keys.
       - Before sending your answer, perform this validation step:
           - Check that "type" is present.
           - Check that "code" is present.
           - Check that "return" is present.
           - If any required key is missing, FIX the JSON before responding.

       The JSON must have this exact schema:
       {
         "type": "table" | "figure",
         "code": "<python code as a string>",
         "return": "result_df" | "result_fig"
       }

       Where:
       "type":
         - "table"  → your code MUST set a pandas DataFrame or Series variable named result_df
         - "figure" → your code MUST set a matplotlib or seaborn Figure variable named result_fig

       "code":
         - Code MUST be a valid JSON string value containing ONLY Python code needed to compute the result.
         - Inside this string:
           - You MAY use normal line breaks; you do NOT need to encode them as "\\n".
           - Use double quotes around string literals and escape them as necessary.
           - Do NOT include comments starting with # unless they are inside the string and properly escaped.            
        - Assume the following are already imported and available: numpy as np,pandas as pd, seaborn as sns, matplotlib.pyplot as plt.
        - If type == "table", your code MUST assign the final DataFrame/Series to a variable named result_df.
        - If type == "figure", your code MUST assign the final Figure to a variable named result_fig.
        - You MUST NOT wrap the code in ``` or """.
        - Code MUST NOT contain any call to plt.show or other display functions.

       "return":
        - The values of "type" and "return" are strictly coupled:
          - If type == "table" then "return" MUST be exactly "result_df"
          - If type == "figure" then "return" MUST be exactly "result_fig"
        - The following combinations are INVALID and MUST NEVER appear:
          - "type": "table" with "return": "result_fig"
          - "type": "figure" with "return": "result_df"

         Examples of a VALID JSON object:
              
         Example 1:
        {
           "type": "figure",
           "code": "import pandas as pd\nimport seaborn as sns\nimport matplotlib.pyplot as plt\n\nsns.boxplot(data=df, orient='h')\nplt.title('Boxplots of House Features')\nplt.xlabel('Feature')\nplt.ylabel('Value')\nresult_fig = plt.gcf()",
           "return": "result_fig"
        }
            
        Example 2:
       {
         "type": "figure",
         "code": "import pandas as pd\nimport matplotlib.pyplot as plt\n\nplt.scatter(df['x_var'], df['y_var'], c=df['y_var'], cmap='viridis')\nplt.title('Relationship between X and Y')\nplt.xlabel('X')\nplt.ylabel('Y')\nresult_fig = plt.gcf()",
         "return": "result_fig"
       }

       Example 3:
       {
         "type": "table",
         "code": "import pandas as pd\n\nresult_df = df.groupby('value_column')['x_var'].sum().sort_values(ascending=False)",
         "return": "result_df"
       }
       </FORMAT_REQUIREMENTS>

       <FINAL_CHECKLIST>
        - Confirm the top-level JSON object has exactly 3 keys: "type", "code", "return".
        - Confirm "code" is a single JSON string value (no nested JSON objects).
        - If any required key is missing, do NOT respond; instead, correct the JSON so all 3 keys are present.
        - Always follow the structure shown in the VALID examples.
        - If type == "table", then return MUST be "result_df" and code MUST set result_df.
        - If type == "figure", then return MUST be "result_fig" and code MUST set result_fig.
        - Combinations like type "table" + return "result_fig" are FORBIDDEN.
        - If type == "figure", then return MUST BE "result_fig" AND code MUST HAVE set result_fig to a matplotlib figure object.
        - Be certain you have called plt.gcf() or ax.figure() and assigned the figure object to result_fig.
        - The response MUST NOT contain ```json, ``` or any Markdown, backticks, comments, or explanatory text.
        - The first character of the JSON response MUST be { and the last character MUST be }.
       </FINAL_CHECKLIST> 
        
     </CRITICAL_REQUIREMENTS>
     '''
  return critical_requirements

def _get_static_rules() -> str:
    return f"""
      FORBIDDEN PATTERNS (NEVER do this):
        - df = pd.read_parquet("...")      # do not load df from a file
        - df = pd.read_csv("...")          # do not load df from a file
        - df = pd.read_excel("...")        # do not load df from a file
        - df = <any expression>            # df is already defined, do not reassign it
        - If your code includes any of the above FORBIDDEN PATTERNS, it will be rejected.
      NO LOOK-BACK RULES:
        - You may NOT repeat or re-emit any complete line of code from earlier sections.
        - You may NOT redefine functions, variables, or classes from earlier sections.
        - If similar logic is required, reimplement it using new names and structure.
      PROGRESS RULES:
        - Each section must introduce new functionality.
        - If no new functionality is needed, STOP generating output.
      - ALWAYS confirm the top-level JSON object has exactly 3 keys: "type", "code", "return".
      - Each key MUST have a value; "type": "<value>", "code": "<value>", "return": "<value>".
      - Both "type" and "code" lines MUST end with a comma. 
    """

def _split_outside_quotes(s: str, sep: str = ",") -> list[str]:
    # Split on commas not inside double quotes
    # (?=(?:[^"]*"[^"]*")*[^"]*$) -> a lookahead ensuring an even number of quotes
    #parts = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', s)
    parts = re.split(rf'{sep}(?=(?:[^"]*"[^"]*")*[^"]*$)', s)
    return [p.strip() for p in parts]

def _memory_to_dict(memory_str: str) -> dict:
    items = _split_outside_quotes(memory_str)
    memory_dict = {}
    
    for item in items:
      #log.debug(f"Processing new memory item => [{item}]")
      try:
            #key, value = item.split(": ", 1)
            key, _, value = item.partition(": ")
            #log.debug(f"Split Memory Item [Key]: {key}\nKey: {key} ->  Value: {value}")
            memory_dict[key.strip()] = value.strip()
      except ValueError: 
            log.warning(f"[ValueError] - Could not parse memory item: {item}")
            continue# Handle cases where with no colon or value
            
    return memory_dict
    
def _parse_string_to_yaml(memory_str: str) -> str:
   memory_dict = _memory_to_dict(memory_str)
   yaml_str = yaml.dump(memory_dict)
   log.debug(f"[YAML] - Parsed memory to yaml:\n {yaml_str}")
   return yaml_str

def _get_memories(memories: list[dict]) -> str:
    memory_context = ""
    if memories:
      for mem in memories:
          memory_str = mem.get(MEMORY_KEY, "")
          if memory_str:
            memory_context += f"- {_parse_string_to_yaml(memory_str)}\n"
      memory_context += "\n"
    return memory_context

def build_new_coding_prompt(question: str, pydc: PydcSessionWrapper, memories: list[dict] = None) -> list[dict[str, str]]:
    df_info = _get_df_info(pydc, rows=5)
    
    prompt = [
        {"role":  "system", "content": f'''
        You are a sought after elite professional Python Software Engineer who always writes clear, concise and bug-free code. 
        Your code can be guaranteed to run flawlessly in production systems. Your task is to write Python code that:

          - Answers the user's specific question with correct, efficient, idiomatic numpy/pandas/matplotlib code.
          - Provides a clear, reliable solution over creative or unusual implementations.
          - Prefers vectorized pandas operations over explicit Python loops over DataFrame rows.
          - Uses meaningful variable names and clear structure; avoids overly clever one-liners.
          - When creating plots, includes axis labels and a title that matches the question.
          - Never uses .show() or display() in the code.
          - Does NOT read or write files and does NOT access the network.
          - When the user asks for a regression line on a scatter plot:
            - You MUST fit y as a function of x using numpy.polyfit, not plot x vs x.
            - Does NOT use plt.plot(df['price'], df['price'], ...) or any x vs x pattern.
          
          {_get_critical_requirements()}
          
          '''
        },{"role": "user", "content": f"""
          Here is information about the user's dataframe (variable name: `df`):
          {df_info}

          <RULES>
          - Do NOT write comments outside the code string.
          - You MUST NOT call pd.read_csv, pd.read_parquet, pd.read_excel, open(), or any other file I/O.
          - You MUST NOT re-create df. Just use the existing df.
          - You MUST always write code that directly operates on the provided dataframe "df".
          - If type == "figure", then return WILL be "result_fig" AND code MUST HAVE set result_fig to a matplotlib figure object.
          - Be certain you have called plt.gcf() or ax.figure() and assigned the figure object to result_fig.
          
          {_get_static_rules()}
                
          </RULES>

          <USER_QUESTION>
          {question}
          </USER_QUESTION>

          """
        }
      ]
    return prompt

def build_editing_code_prompt(question: str, pydc: PydcSessionWrapper, memories: list[dict] = None) -> list[dict[str, str]]:
    memory_context = _get_memories(memories)
    df_info = _get_df_info(pydc, rows=5)
    current_code = pydc.generated_code
   
    log.info(f"<CURRENT_CODE>:\n{current_code}\n")
         
    prompt = [
       {"role":  "system", "content": f'''
       You are a sought after elite professional Python Software Engineer who can patch existing code and guarantee clear, concise and bug-free code. 
       Your code can be guaranteed to run flawlessly in production systems. Your task is to patch the Python code in the <CURRENT_CODE> section to:
            
       - Address the user's modification with correct, efficient, idiomatic numpy/pandas/matplotlib code.
       - Provides a clear, reliable solution over creative or unusual implementations.
       - Prefers vectorized pandas operations over explicit Python loops over DataFrame rows.
       - Uses meaningful variable names and clear structure; avoids overly clever one-liners.
       - When creating plots, includes axis labels and a title that matches the question.
       - Never uses .show() or display() in the code.
       - Does NOT read or write files and does NOT access the network.
       - When the user asks for a regression line on a scatter plot:
         - You MUST fit y as a function of x using numpy.polyfit, not plot x vs x.
         - Does NOT use plt.plot(df['price'], df['price'], ...) or any x vs x pattern.
            
       {_get_critical_requirements()}
             
     '''
   },{"role": "user", "content": f"""
     Carefully read and use the information inside <MEMORIES> when answering.
     
    <RULES>
     - Treat <CURRENT_CODE> as the starting point and apply the new request in <USER_QUESTION> as an incremental change to it.
     - You SHOULD preserve the overall structure and logic of <CURRENT_CODE>.
     - You MUST NOT remove or omit any line from <CURRENT_CODE> that is required for the code to run correctly (for example, variable definitions, copies like result_df = df.copy(), or imports) unless the user explicitly asks to remove or change that behavior.
     - You MAY refactor or adjust existing lines when it is clearly required to correctly implement the new request, to fix a bug, or to improve clarity, but the resulting code MUST still perform all previously implemented steps.
     - When you modify existing behavior, you SHOULD:
       - Keep the intent of the original code, and
       - Make the smallest reasonable set of edits needed (e.g., adjust parameters, add arguments, insert a few new lines, or slightly restructure a block).
     - If <CURRENT_CODE> defines result_df from df (for example, result_df = df.copy() or result_df = some_expression_using_df), your new code MUST still define result_df in a way that includes all previous columns and calculations, plus the new changes.
     - You MUST ensure that all previously requested and implemented features and steps still exist in your final code (for example, creation of result_df and any previously added columns), unless the user has asked to remove or replace them.
     - Do NOT write comments outside the code string.
     - You MUST NOT call pd.read_csv, pd.read_parquet, pd.read_excel, open(), or any other file I/O.
     - You MUST NOT re-create df. Just use the existing df.
     - You MUST always write code that directly operates on the provided dataframe "df".
     - You MUST NOT call pd.read_csv, pd.read_parquet, pd.read_excel, open(), or any other file I/O.
     - You MUST NOT re-create df. Just use the existing df.
     - Always write code that directly operates on the existing df.
     - If type == "figure", then return WILL be "result_fig" AND code MUST HAVE set result_fig to a matplotlib figure object.
     - Be certain you have called plt.gcf() or ax.figure() and assigned the figure object to result_fig.
     
     {_get_static_rules()}
     
     - Treat <MEMORIES> as trusted background about the user, their preferences, past queries, and previous results.
     - <MEMORIES> include an ISO 8601 timestamp; Treat memories with later timestamps as more recent.
     - If memories conflict, you MUST follow the most recent applicable memory.
     - Items marked as "SUMMARY" are not full code, but a summary of earlier code or outputs.
     - Treat them as high-level descriptions, not exact code to be copied.
     - If a memory has status: incorrect or similar, do NOT repeat that behavior; instead, follow the latest correction or lesson.
     </RULES>
          
     <MEMORIES>
      {memory_context}
     </MEMORIES>

     Here is information about the user's dataframe (variable name: `df`):
     {df_info}

     <CURRENT_CODE>
     {current_code}
     </CURRENT_CODE>

     <USER_QUESTION>
     {question}
     </USER_QUESTION>

      """
      }
    ]
    return prompt