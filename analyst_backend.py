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

load_dotenv()
hf_token = os.getenv("HUGGINGFACE_TOKEN")
client = InferenceClient(provider = "auto", api_key = hf_token)
model_name = "meta-llama/Llama-3.1-8B-Instruct"

def Data_Cleaning(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    total_rows = int(df.shape[0])
    total_cols = int(df.shape[1])
    df_shape = df.shape


    duplicate_count = int(df.duplicated().sum())
    nulls_per_column = df.isnull().sum().to_dict()
    total_nulls = int(df.isnull().sum().sum())

    null_percentages = {}
    if total_rows > 0:
        null_percentages = {col: round((count / total_rows) * 100, 2) for col, count in nulls_per_column.items()}

    column_types = {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
    report = {
        "shape": df_shape,
        "total_rows": total_rows,
        "total_columns": total_cols,
        "duplicate_count": duplicate_count,
        "total_nulls": total_nulls,
        "nulls_per_column": nulls_per_column,
        "null_percentages_per_column": null_percentages,
        "column_types": column_types
    }

    return report


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
    2. Ensure the code does NOT contain malicious commands like 'os.system', 'eval(input())', or file deletion.
    3. Ensure the code actually attempts to solve the user's request.

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

    DATASET SCHEMA & HEALTH METRICS:
    {formatted_schema}
    - Exact Duplicate Rows Detected: {quality_report['duplicate_count']}
    - Cumulative Missing Values: {quality_report['total_nulls']}

    CRITICAL INSTRUCTIONS:
    1. Write ONLY executable Python code using pandas, numpy, plotly.express (as px), or matplotlib.pyplot (as plt).
    2. BEFORE performing any calculations, analysis, or generating charts, you MUST write the code to clean the data first (e.g., handling the duplicates or missing values specified in the health metrics above if they affect the columns needed).
    3. If the user explicitly asks to clean data, fix duplicates, or handle missing values, dynamically write the code to clean the dataset and reassign it back to 'df'.
    4. If the user asks for a chart or visual diagram, you MUST save the final plotting object into a local variable explicitly named 'fig' (e.g., fig = px.bar(df, x='category', y='popularity')). Do NOT import streamlit, do NOT call st.plotly_chart, and do NOT use plt.show(). Return only the logic assigning the object to 'fig'.
    5. Return nothing but the raw executable Python code wrapped inside a markdown block (```python ... ```). Do not include conversational text, pleasantries, or explanations.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    try:
        response = client.chat_completion(
            model=model_name,
            messages=messages,
            max_tokens=600,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating code from Llama: {str(e)}"


def generate_and_verify_pipeline(user_query, df, quality_report):
    attempts = 0
    max_attempts = 3
    feedback_string = None  # Start clean without pre-baked feedback strings

    while attempts < max_attempts:
        # Build a fresh, clean query providing only the LATEST context/criticism
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

# ... (Keep Data_Cleaning, Importing_Data, critic_validate_code, and generate_and_verify_pipeline completely the same)

def execute_generated_code(code_string, df):
    # --- Air-tight Code Block Stripping Logic ---
    cleaned = re.sub(r'^```[a-zA-Z]*\s*\n', '', code_string, flags=re.MULTILINE | re.IGNORECASE)
    cleaned = re.sub(r'\n```\s*$', '', cleaned, flags=re.MULTILINE)

    lines = cleaned.split('\n')
    if lines and lines[0].strip().lower() in ['python', 'bash', 'py']:
        lines.pop(0)

    clean_code = '\n'.join(lines).strip()
    # ---------------------------------------------

    execution_context = {
        "df": df,
        "pd": pd,
        "np": np,
        "px": px,
        "plt": plt
    }

    # Intercept standard output streams to log print statement results
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output

    try:
        # Run the fully sanitized code string safely in isolation
        exec(clean_code, {}, execution_context)

        # Restore normal stdout stream tracking
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