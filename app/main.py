"""
FastAPI application for the AI grading service.
Exposes endpoints for:
1. POST /analyze-solution - Generate grading blueprint from teacher's solution
2. POST /grade-submission - Grade a student submission against blueprint
3. GET /health - Health check
"""

import os
import asyncio
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from dotenv import load_dotenv
from openai import OpenAI

# Import your existing modules
from app.parse_pdfs import extract_text_from_pdf
from app.prompt_gen import build_grading_prompt

# Import schemas
from app.schemas import (
    AnalyzeSolutionRequest,
    AnalyzeSolutionResponse,
    GradeSubmissionRequest,
    GradeSubmissionResponse,
    GradingBlueprint,
    GradingResult,
    BlueprintConcept,
    ConceptScore,
    BlueprintCallbackPayload,
    GradingCallbackPayload,
    HealthResponse,
)

load_dotenv()

# ============= Configuration =============

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CALLBACK_SECRET = os.getenv("CALLBACK_SECRET")  # For signing callbacks (optional)
# REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
# REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_URL = os.getenv("REDIS_URL")

# Global Redis client
redis_client: Optional[redis.Redis] = None


# ============= Lifespan Management =============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Redis connection lifecycle"""
    global redis_client
    try:
        # redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        redis_client = redis.from_url(REDIS_URL)
        await redis_client.ping()
        print(f"Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")
        redis_client = None

    yield

    if redis_client:
        await redis_client.close()


# ============= FastAPI App =============

app = FastAPI(
    title="AI Grading Service",
    description="Automated grading service using LLMs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= Helper Functions =============

async def download_pdf(url: str) -> str:
    """Download PDF from pre-signed S3 URL to a temp file, return path"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60.0)
        response.raise_for_status()

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(response.content)
            return f.name


async def send_callback(callback_url: str, payload: dict) -> bool:
    """Send callback to Edge Function"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=payload,
                timeout=30.0,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            print(f"Callback sent successfully: {response.status_code}")
            return True
    except Exception as e:
        print(f"Callback failed: {e}")
        return False


def get_default_rubric() -> dict:
    """Return the default 4-criterion grading rubric"""
    return {
        "total_marks": 100,
        "criteria": {
            "concept_coverage": {
                "weight": 30,
                "description": "Coverage of required theoretical concepts",
                "levels": {
                    "excellent": {"score_range": [26, 30],
                                  "description": "All core concepts are correctly identified and explained"},
                    "good": {"score_range": [20, 25], "description": "Most concepts covered with minor gaps"},
                    "partial": {"score_range": [10, 19], "description": "Some important concepts missing or unclear"},
                    "poor": {"score_range": [0, 9], "description": "Major conceptual misunderstandings"}
                }
            },
            "reasoning_quality": {
                "weight": 25,
                "description": "Logical flow and soundness of reasoning",
                "levels": {
                    "excellent": {"score_range": [21, 25], "description": "Clear, coherent, step-by-step reasoning"},
                    "good": {"score_range": [16, 20], "description": "Mostly logical with minor inconsistencies"},
                    "partial": {"score_range": [8, 15], "description": "Weak or fragmented reasoning"},
                    "poor": {"score_range": [0, 7], "description": "Illogical or unsupported arguments"}
                }
            },
            "correctness": {
                "weight": 30,
                "description": "Accuracy of facts, equations, and conclusions",
                "levels": {
                    "excellent": {"score_range": [26, 30], "description": "All derivations and statements are correct"},
                    "good": {"score_range": [20, 25], "description": "Minor computational or factual errors"},
                    "partial": {"score_range": [10, 19], "description": "Multiple errors affecting correctness"},
                    "poor": {"score_range": [0, 9], "description": "Mostly incorrect or invalid solution"}
                }
            },
            "clarity": {
                "weight": 15,
                "description": "Clarity, structure, and presentation",
                "levels": {
                    "excellent": {"score_range": [13, 15], "description": "Well-structured, clear, and easy to follow"},
                    "good": {"score_range": [10, 12], "description": "Understandable but slightly messy"},
                    "partial": {"score_range": [5, 9], "description": "Hard to follow"},
                    "poor": {"score_range": [0, 4], "description": "Unclear or poorly presented"}
                }
            }
        }
    }


# ============= Core Grading Logic =============

def analyze_solution_sync(solution_text: str, rubric: dict) -> GradingBlueprint:
    """
    Analyze teacher's solution to extract grading blueprint.
    This identifies key concepts, expected steps, and facts to check for.
    """
    client = OpenAI()

    analysis_prompt = f"""
You are an expert academic grader. Analyze the following teacher's solution and extract a grading blueprint.

SOLUTION:
\"\"\"
{solution_text}
\"\"\"

RUBRIC WEIGHTS:
{rubric}

Extract the following in JSON format:
{{
    "concepts": [
        {{"name": "concept name", "weight": points, "description": "what student must demonstrate"}}
    ],
    "expected_steps": ["step 1", "step 2", ...],
    "key_facts": ["fact that must be correct", ...],
    "rubric": {{"concept_coverage": 30, "reasoning_quality": 25, "correctness": 30, "clarity": 15}}
}}

Be specific and actionable. These will be used to grade student submissions.
"""

    response = client.chat.completions.create(
        model="gpt-4o",  # Use gpt-4o for analysis
        messages=[
            {"role": "system", "content": "You are an expert academic grader. Output valid JSON only."},
            {"role": "user", "content": analysis_prompt}
        ],
        response_format={"type": "json_object"},
    )

    import json
    result = json.loads(response.choices[0].message.content)

    # Convert to GradingBlueprint
    concepts = [
        BlueprintConcept(name=c["name"], weight=c["weight"], description=c["description"])
        for c in result.get("concepts", [])
    ]

    return GradingBlueprint(
        concepts=concepts,
        expected_steps=result.get("expected_steps", []),
        key_facts=result.get("key_facts", []),
        rubric=result.get("rubric",
                          {"concept_coverage": 30, "reasoning_quality": 25, "correctness": 30, "clarity": 15}),
        total_points=100,
    )


def grade_submission_sync(
        student_text: str,
        teacher_text: str,
        blueprint: GradingBlueprint,
        rubric: dict,
        metadata: dict
) -> GradingResult:
    """
    Grade a student submission against the teacher's solution using the blueprint.
    """
    client = OpenAI()

    # Use your existing prompt builder
    grading_prompt = build_grading_prompt(
        assignment_metadata=metadata,
        grading_rubric=rubric,
        teacher_solution=teacher_text,
        student_solution=student_text
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a strict academic grader. Output valid JSON only."},
            {"role": "user", "content": grading_prompt}
        ],
        response_format={"type": "json_object"},
    )

    import json
    result = json.loads(response.choices[0].message.content)

    # Parse the LLM output into GradingResult format
    overall = result.get("overall_score", {})

    # Build concept_scores from rubric_breakdown
    concept_scores = {}
    for breakdown in result.get("rubric_breakdown", []):
        criterion = breakdown.get("criterion", "").lower().replace(" ", "_")
        # Map to standard keys
        key_map = {
            "concept_coverage": "concept_coverage",
            "logical_reasoning": "reasoning_quality",
            "reasoning": "reasoning_quality",
            "reasoning_quality": "reasoning_quality",
            "logical_reasoning_&_structure": "reasoning_quality",
            "correctness": "correctness",
            "correctness_&_accuracy": "correctness",
            "clarity": "clarity",
            "clarity_&_presentation": "clarity",
        }
        key = key_map.get(criterion, criterion)

        concept_scores[key] = ConceptScore(
            earned=breakdown.get("awarded_marks", 0),
            max=breakdown.get("max_marks", 0),
            feedback=breakdown.get("evaluation", "")
        )

    # Ensure all 4 criteria exist
    for key, max_pts in [("concept_coverage", 30), ("reasoning_quality", 25), ("correctness", 30), ("clarity", 15)]:
        if key not in concept_scores:
            concept_scores[key] = ConceptScore(earned=0, max=max_pts, feedback="Not evaluated")

    return GradingResult(
        score=overall.get("obtained", 0),
        max_score=overall.get("maximum", 100),
        concept_scores=concept_scores,
        overall_feedback=result.get("final_verdict", {}).get("summary", ""),
        strengths=[],  # Could parse from actionable_feedback
        improvements=result.get("actionable_feedback", []),
        plagiarism_flag=False,  # Implement plagiarism check separately if needed
    )


# ============= Background Tasks =============

async def process_blueprint_generation(
        assignment_id: str,
        solution_pdf_url: str,
        callback_url: str,
        rubric: Optional[dict] = None
):
    """Background task: Download PDF, analyze, send callback"""
    try:
        # Update job status in Redis
        if redis_client:
            await redis_client.set(f"job:blueprint:{assignment_id}", "processing")

        # Download PDF
        pdf_path = await download_pdf(solution_pdf_url)

        # Extract text
        solution_text = extract_text_from_pdf(pdf_path)

        # Analyze solution
        use_rubric = rubric or get_default_rubric()
        blueprint = analyze_solution_sync(solution_text, use_rubric)

        # Send success callback
        callback_payload = BlueprintCallbackPayload(
            assignment_id=assignment_id,
            blueprint=blueprint
        )
        await send_callback(callback_url, callback_payload.model_dump())

        # Update job status
        if redis_client:
            await redis_client.set(f"job:blueprint:{assignment_id}", "completed")

        # Cleanup temp file
        os.unlink(pdf_path)

    except Exception as e:
        print(f"Blueprint generation failed: {e}")
        # Send error callback
        callback_payload = BlueprintCallbackPayload(
            assignment_id=assignment_id,
            error=str(e)
        )
        await send_callback(callback_url, callback_payload.model_dump())

        if redis_client:
            await redis_client.set(f"job:blueprint:{assignment_id}", f"failed:{str(e)}")


async def process_grading(
        submission_id: str,
        assignment_id: str,
        submission_pdf_url: str,
        blueprint: GradingBlueprint,
        callback_url: str
):
    """Background task: Download PDF, grade, send callback"""
    try:
        # Update job status in Redis
        if redis_client:
            await redis_client.set(f"job:grade:{submission_id}", "processing")

        # Download student submission PDF
        pdf_path = await download_pdf(submission_pdf_url)

        # Extract text
        student_text = extract_text_from_pdf(pdf_path)

        # For grading, we need the teacher's solution text too
        # In a real implementation, you'd store this or re-fetch it
        # For now, use the blueprint's expected_steps as reference
        teacher_text = "\n".join(blueprint.expected_steps + blueprint.key_facts)

        # Grade submission
        rubric = get_default_rubric()
        metadata = {
            "assignment_id": assignment_id,
            "course_name": "Course",
            "topic": "Topic",
            "difficulty_level": "medium"
        }

        grading_result = grade_submission_sync(
            student_text=student_text,
            teacher_text=teacher_text,
            blueprint=blueprint,
            rubric=rubric,
            metadata=metadata
        )

        # Send success callback
        callback_payload = GradingCallbackPayload(
            submission_id=submission_id,
            grading_result=grading_result
        )
        await send_callback(callback_url, callback_payload.model_dump())

        # Update job status
        if redis_client:
            await redis_client.set(f"job:grade:{submission_id}", "completed")

        # Cleanup temp file
        os.unlink(pdf_path)

    except Exception as e:
        print(f"Grading failed: {e}")

        if redis_client:
            await redis_client.set(f"job:grade:{submission_id}", f"failed:{str(e)}")


# ============= API Endpoints =============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    redis_ok = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_ok = True
        except:
            pass

    return HealthResponse(
        status="healthy",
        redis_connected=redis_ok
    )


@app.post("/analyze-solution", response_model=AnalyzeSolutionResponse)
async def analyze_solution(
        request: AnalyzeSolutionRequest,
        background_tasks: BackgroundTasks
):
    """
    Trigger blueprint generation from teacher's solution.
    Processing happens asynchronously; result is sent via callback.
    """
    job_id = f"blueprint_{request.assignment_id}"

    # Queue the background task
    background_tasks.add_task(
        process_blueprint_generation,
        assignment_id=request.assignment_id,
        solution_pdf_url=request.solution_pdf_url,
        callback_url=request.callback_url,
        rubric=request.rubric.model_dump() if request.rubric else None
    )

    return AnalyzeSolutionResponse(
        success=True,
        message="Blueprint generation started",
        job_id=job_id
    )


@app.post("/grade-submission", response_model=GradeSubmissionResponse)
async def grade_submission(
        request: GradeSubmissionRequest,
        background_tasks: BackgroundTasks
):
    """
    Trigger grading of a student submission.
    Processing happens asynchronously; result is sent via callback.
    """
    job_id = f"grade_{request.submission_id}"

    # Queue the background task
    background_tasks.add_task(
        process_grading,
        submission_id=request.submission_id,
        assignment_id=request.assignment_id,
        submission_pdf_url=request.submission_pdf_url,
        blueprint=request.grading_blueprint,
        callback_url=request.callback_url
    )

    return GradeSubmissionResponse(
        success=True,
        message="Grading started",
        job_id=job_id
    )


# ============= Run with Uvicorn =============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
