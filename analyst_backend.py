import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
import re
import io
import sys
from fastapi.encoders import jsonable_encoder

load_dotenv()
hf_token = os.getenv("HUGGINGFACE_TOKEN")
client = InferenceClient(provider = "auto", api_key = hf_token)
model_name = "meta-llama/Llama-3.1-8B-Instruct"

def Data_Cleaning(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    total_rows = int(df.shape[0])
    total_cols = int(df.shape[1])
    df_shape = [int(total_rows), int(total_cols)]

    duplicate_count = int(df.duplicated().sum())
    nulls_per_column = {str(col): int(count) for col, count in df.isnull().sum().to_dict().items()}
    total_nulls = int(df.isnull().sum().sum())

    null_percentages = {}
    if total_rows > 0:
        null_percentages = {str(col): round((count / total_rows) * 100, 2) for col, count in nulls_per_column.items()}

    column_types = {str(col): str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
    report = {
        "shape": df_shape,
        "total_rows": total_rows,
        "total_columns": total_cols,
        "columns": list(df.columns),
        "duplicate_count": duplicate_count,
        "total_nulls": total_nulls,
        "nulls_per_column": nulls_per_column,
        "null_percentages_per_column": null_percentages,
        "column_types": column_types
    }

    return jsonable_encoder(report)


def Importing_Data(uploaded_file):
    file_name = uploaded_file.name.lower()

    try:
        if file_name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        elif file_name.endswith(".json"):
            df = pd.read_json(uploaded_file)
        else:
            return {"status": "Invalid file type" , "df":None, "report":None}

        if df is not None:
            quality_report = Data_Cleaning(df)
            return {"status": "Success", "df": df, "report": quality_report}

    except Exception as e:
        return {"status":f"Error Loading File: {str(e)}", "df":None, "report":None}


def critic_validate_code(user_query, generated_code, quality_report):
    system_prompt = f"""
    You are a Senior Code Reviewer and Security Guard. 
    Your job is to inspect generated Python code meant to run on a DataFrame named 'df'.

    VALID COLUMNS AVAILABLE: {list(quality_report['column_types'].keys())}

    CRITICAL INSPECTION RULES:
    1. Check if all column names used in the code are spelled EXACTLY as shown in the list above.
    2. STRING FILTERING RULE: If the code filters text values (like club names or player names), ensure it accounts for partial matches or exact dataset naming syntax. For example, use `.str.contains('Barcelona', case=False, na=False)` instead of `== 'Barcelona'` to prevent returning empty datasets (`nan`).
    3. Ensure the code does NOT contain malicious commands like 'os.system', 'eval(input())', or file deletion.
    4. Ensure the code actually attempts to solve the user's request.

    RESPONSE FORMAT:
    - If the code is perfect and safe, respond with ONLY the single word: "PASSED"
    - If there is an issue, explain exactly what is wrong or what typo exists so the developer model can fix it.
    """

    user_prompt = f"User Request: {user_query}\n\nGenerated Code to Inspect:\n{generated_code}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        response = client.chat_completion(
            model=model_name,
            messages=messages,
            max_tokens=200,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Critic Error: {str(e)}"


def ask_llama_to_generate_code(user_query, df, quality_report):
    columns_and_types = quality_report["column_types"]
    null_percentages = quality_report["null_percentages_per_column"]

    formatted_schema = ""
    for col, dtype in columns_and_types.items():
        missing_pct = null_percentages.get(col, 0.0)
        formatted_schema += f"- {col} ({dtype}) | Missing: {missing_pct}%\n"

    system_prompt = f"""
    You are an expert Python data analyst operating on a Pandas DataFrame named 'df'.

    DATASET DIMENSIONS:
    - Total Rows: {quality_report['total_rows']}
    - Total Columns: {quality_report['total_columns']}
    - Matrix Shape: {quality_report['shape']}
    - Complete Column List: {quality_report['columns']}

    DATASET SCHEMA & HEALTH METRICS:
    {formatted_schema}
    - Exact Duplicate Rows Detected: {quality_report['duplicate_count']}
    - Cumulative Missing Values: {quality_report['total_nulls']}

    CRITICAL INSTRUCTIONS:
    You are an expert Senior Data Analyst and elite Python Engineer. Your task is to write clean, executable Python code to inspect, clean, analyze, or visualize a pandas DataFrame named 'df'. 

Follow these strict constraints at all times:
1. RESPONSE FORMAT: Output ONLY raw, executable Python code wrapped inside a markdown block (```python ... ```). Do not include any introductory text, pleasantries, markdown titles, or explanations outside the code block.

2. MATH & EXECUTION SAFETY: 
   - Never assume column data types. Check them or convert them using broad context-aware logic before running operations.
   - When converting currency, scale metrics, or cleaning string characters (like $, €, K, M), you MUST write robust conversion workflows that preserve value magnitudes (e.g., parsing '20K' mathematically into 20000, and '5M' into 5000000). Never discard the scale factor.

3. WORKSPACE VISUALIZATION RULES:
   - If the user asks for a chart, plot, or graph (e.g., distribution histograms, line charts, scatter plots, or correlation heatmaps), you MUST save the final chart object into a local variable explicitly named 'fig'.
   - To ensure visual fluidity inside the web app dashboard, keep the layout background transparent or default so it seamlessly inherits the web platform's theme. Do NOT apply dark templates like template='plotly_dark'.
   - CRITICAL: Never call fig.show(), plt.show(), or st.plotly_chart(). Simply declare 'fig' at the end and let the script terminate naturally.

4. CORE EDA & ANALYSIS RULES:
   - When asked for "EDA" or exploratory data analysis, perform a deep mathematical deep-dive: compute comprehensive summary metrics (.describe(), means, medians) strictly on numeric columns using `df.select_dtypes(include=[np.number])`.
   - For visual data summaries, construct an optimized overview graphic assigned directly to 'fig' (such as a distribution plot of a key feature or a breakdown of dominant categories).
   - If a correlation matrix heatmap is requested, ensure non-numeric columns are explicitly excluded before running `.corr()` to prevent syntax execution failures.

5. SUBJECTIVE & STRATEGIC SUBMISSIONS:
   - If the query demands a subjective conclusion, business reasoning, or data-driven justification, you MUST output a beautifully formatted text report using explicit section dividers (---), bullet points (*), and structured key-value summaries contained entirely within a standard Python `print()` statement execution block. 
   - Explain the strategic "why" metrics cleanly based directly on data observations instead of printing raw unformatted technical objects.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    try:
        response = client.chat_completion(
            model=model_name,
            messages=messages,
            max_tokens=1000,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating code from Llama: {str(e)}"


def generate_and_verify_pipeline(user_query, df, quality_report):
    attempts = 0
    max_attempts = 3
    feedback_string = None

    while attempts < max_attempts:
        if feedback_string:
            active_query = (
                f"User Request: {user_query}\n\n"
                f"YOUR PREVIOUS ATTEMPT FAILED CRITIC REVIEW:\n{feedback_string}\n\n"
                f"Fix the code based on the feedback above. Ensure it matches the requested behavior exactly."
            )
        else:
            active_query = user_query

        generated_code = ask_llama_to_generate_code(active_query, df, quality_report)
        critic_review = critic_validate_code(user_query, generated_code, quality_report)

        if "PASSED" in critic_review.upper():
            return {
                "success": True,
                "code": generated_code,
                "iterations": attempts + 1
            }

        feedback_string = critic_review
        attempts += 1

    return {
        "success": False,
        "code": generated_code,
        "iterations": max_attempts
    }


def execute_generated_code(code_string, df):
    cleaned = re.sub(r'^```[a-zA-Z]*\s*\n', '', code_string, flags=re.MULTILINE | re.IGNORECASE)
    cleaned = re.sub(r'\n```\s*$', '', cleaned, flags=re.MULTILINE)

    lines = cleaned.split('\n')
    if lines and lines[0].strip().lower() in ['python', 'bash', 'py']:
        lines.pop(0)

    clean_code = '\n'.join(lines).strip()

    execution_context = {
        "df": df,
        "pd": pd,
        "np": np,
        "px": px,
        "plt": plt
    }

    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output

    try:
        exec(clean_code, {}, execution_context)

        sys.stdout = old_stdout
        captured_text = redirected_output.getvalue()

        updated_df = execution_context.get("df", df)
        generated_chart = execution_context.get("fig", None)

        return {
            "success": True,
            "df": updated_df,
            "chart": generated_chart,
            "output_text": captured_text,
            "error": None
        }
    except Exception as e:
        sys.stdout = old_stdout
        return {
            "success": False,
            "df": df,
            "chart": None,
            "output_text": "",
            "error": str(e)
        }