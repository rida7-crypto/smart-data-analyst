import os
from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import io
import plotly.io as pio

# Import your rock-solid backend functions
from analyst_backend import Importing_Data, generate_and_verify_pipeline, execute_generated_code, Data_Cleaning
app = FastAPI()

# Get absolute path of current directory to prevent file path errors
current_dir = os.path.dirname(os.path.realpath(__file__))

# Link your custom static assets and HTML templates
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

# Global in-memory storage variables for active sessions
# (In production, this would be a session cache, but this works perfectly for single user testing)
state = {
    "df": None,
    "report": None
}


@app.get("/", response_class=HTMLResponse)
async def render_homepage(request: Request):
    """Serves your beautiful, custom styled HTML landing layout."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/upload")
async def handle_file_upload(file: UploadFile = File(...)):
    """Receives the dropped file from HTML and routes it through the profiling engine."""
    try:
        contents = await file.read()
        # Convert raw binary contents into an in-memory stream object
        file_stream = io.BytesIO(contents)
        file_stream.name = file.filename  # Maintain extension for parsing logic

        # Trigger your backend pipeline stage 1 & 2
        result = Importing_Data(file_stream)

        if result["status"] == "Success":
            state["df"] = result["df"]
            state["report"] = result["report"]

            # Return JSON analytics back to the HTML page
            return JSONResponse(content={
                "status": "Success",
                "metrics": state["report"]
            })
        else:
            return JSONResponse(content={"status": "Error", "message": result["status"]}, status_code=400)

    except Exception as e:
        return JSONResponse(content={"status": "Error", "message": str(e)}, status_code=500)


# ... (Keep app imports and state declaration exactly the same)

@app.post("/analyze")
async def handle_analysis_query(query: str = Form(...)):
    if state["df"] is None or state["report"] is None:
        return JSONResponse(
            content={"status": "Error", "message": "No active dataset initialized. Upload a file first."},
            status_code=400)

    try:
        pipeline_result = generate_and_verify_pipeline(query, state["df"], state["report"])

        if not pipeline_result["success"]:
            return JSONResponse(content={
                "status": "Failed Validation",
                "message": "The Critic agent rejected the generated execution scripts after 3 safety adjustments.",
                "code_draft": pipeline_result["code"]
            }, status_code=422)

        execution_result = execute_generated_code(pipeline_result["code"], state["df"])

        if not execution_result["success"]:
            return JSONResponse(content={
                "status": "Execution Crash",
                "message": execution_result["error"]
            }, status_code=500)

        # Sync our core in-memory dataframe state alterations
        state["df"] = execution_result["df"]
        state["report"] = Data_Cleaning(state["df"])  # Recalculate live layout structure

        chart_json = None
        fig = execution_result.get("chart")
        if fig is not None:
            chart_json = pio.to_json(fig)

        return JSONResponse(content={
            "status": "Success",
            "iterations": pipeline_result["iterations"],
            "code_run": pipeline_result["code"],
            "has_chart": chart_json is not None,
            "chart_data": chart_json,
            "output_text": execution_result["output_text"],  # Send console log strings down
            "metrics": state["report"],  # Send fresh metrics to update sidebar fields
            "data_preview": state["df"].head(5).to_dict(orient="records")
        })

    except Exception as e:
        return JSONResponse(content={"status": "Error", "message": str(e)}, status_code=500)