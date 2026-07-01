import os
from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import io
import plotly.io as pio

from analyst_backend import Importing_Data, generate_and_verify_pipeline, execute_generated_code, Data_Cleaning
app = FastAPI()

current_dir = os.path.dirname(os.path.realpath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

state = {
    "df": None,
    "report": None
}


@app.get("/", response_class=HTMLResponse)
async def render_homepage(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/upload")
async def handle_file_upload(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        file_stream = io.BytesIO(contents)
        file_stream.name = file.filename

        result = Importing_Data(file_stream)

        if result["status"] == "Success":
            state["df"] = result["df"]
            state["report"] = result["report"]

            return JSONResponse(content={
                "status": "Success",
                "metrics": state["report"]
            })
        else:
            return JSONResponse(content={"status": "Error", "message": result["status"]}, status_code=400)

    except Exception as e:
        return JSONResponse(content={"status": "Error", "message": str(e)}, status_code=500)


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

        state["df"] = execution_result["df"]
        state["report"] = Data_Cleaning(state["df"])

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
            "output_text": execution_result["output_text"],
            "metrics": state["report"],
            "data_preview": state["df"].head(5).to_dict(orient="records")
        })

    except Exception as e:
        return JSONResponse(content={"status": "Error", "message": str(e)}, status_code=500)