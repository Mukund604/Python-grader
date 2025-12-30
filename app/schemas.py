"""
Pydantic schemas for the grading service API.
These must match the data formats expected by the Supabase Edge Function.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


# ============= Rubric Structures =============

class RubricLevel(BaseModel):
    """A single level within a rubric criterion (e.g., 'excellent', 'good')"""
    score_range: List[int] = Field(..., min_items=2, max_items=2)
    description: str


class RubricCriterion(BaseModel):
    """A single rubric criterion (e.g., 'concept_coverage')"""
    weight: int
    description: str
    levels: Dict[str, RubricLevel]  # Keys: excellent, good, partial, poor


class GradingRubric(BaseModel):
    """The complete grading rubric structure"""
    total_marks: int = 100
    criteria: Dict[str, RubricCriterion]


class AssignmentMetadata(BaseModel):
    """Metadata about the assignment being graded"""
    assignment_id: str
    course_name: Optional[str] = None
    topic: Optional[str] = None
    difficulty_level: Optional[str] = "medium"
    expected_length: Optional[str] = None


# ============= Blueprint Structures =============
# These MUST match the GradingBlueprint interface in the Edge Function

class BlueprintConcept(BaseModel):
    """A concept extracted from the teacher's solution"""
    name: str
    weight: int  # Points for this concept
    description: str


class GradingBlueprint(BaseModel):
    """
    The grading blueprint generated from the teacher's solution.
    This is stored in the database and used to grade all student submissions.

    MUST MATCH Edge Function's GradingBlueprint interface:
    - concepts: Array of {name, weight, description}
    - expected_steps: string[]
    - key_facts: string[]
    - rubric: Record<string, number>
    - total_points: number
    - created_at: string (ISO format)
    """
    concepts: List[BlueprintConcept]
    expected_steps: List[str]
    key_facts: List[str]
    rubric: Dict[str, int]  # e.g., {"concept_coverage": 30, "reasoning_quality": 25}
    total_points: int = 100
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============= Grading Result Structures =============
# These MUST match the GradingResult interface in the Edge Function

class ConceptScore(BaseModel):
    """Score and feedback for a single concept/criterion"""
    earned: int
    max: int
    feedback: str


class GradingResult(BaseModel):
    """
    The complete grading result for a student submission.

    MUST MATCH Edge Function's GradingResult interface:
    - score: number
    - max_score: number
    - concept_scores: Record<string, {earned, max, feedback}>
    - overall_feedback: string
    - strengths: string[]
    - improvements: string[]
    - plagiarism_flag: boolean
    - plagiarism_details?: string
    - graded_at: string (ISO format)
    """
    score: int
    max_score: int = 100
    concept_scores: Dict[str, ConceptScore]  # Keys match rubric criteria
    overall_feedback: str
    strengths: List[str]
    improvements: List[str]
    plagiarism_flag: bool = False
    plagiarism_details: Optional[str] = None
    graded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============= API Request/Response Schemas =============

class AnalyzeSolutionRequest(BaseModel):
    """
    Request body for POST /analyze-solution
    Sent by Edge Function's triggerBlueprintGeneration()
    """
    assignment_id: str
    solution_pdf_url: str  # Pre-signed S3 download URL
    callback_url: str  # Edge function URL for callback

    # Optional: custom rubric (defaults to standard 4-criterion rubric)
    rubric: Optional[GradingRubric] = None
    metadata: Optional[AssignmentMetadata] = None


class AnalyzeSolutionResponse(BaseModel):
    """Immediate response from /analyze-solution (async processing)"""
    success: bool
    message: str
    job_id: str  # For tracking the async job


class GradeSubmissionRequest(BaseModel):
    """
    Request body for POST /grade-submission
    Sent by Edge Function's triggerGrading()
    """
    submission_id: str
    assignment_id: str
    submission_pdf_url: str  # Pre-signed S3 download URL
    grading_blueprint: GradingBlueprint  # From database
    callback_url: str  # Edge function URL for callback


class GradeSubmissionResponse(BaseModel):
    """Immediate response from /grade-submission (async processing)"""
    success: bool
    message: str
    job_id: str


# ============= Callback Payloads =============
# These are sent TO the Edge Function when processing completes

class BlueprintCallbackPayload(BaseModel):
    """
    Callback payload for blueprint generation completion.
    Edge Function expects: { action, assignment_id, blueprint?, error? }
    """
    action: str = "blueprint-callback"
    assignment_id: str
    blueprint: Optional[GradingBlueprint] = None
    error: Optional[str] = None


class GradingCallbackPayload(BaseModel):
    """
    Callback payload for grading completion.
    Edge Function expects: { action, submission_id, grading_result }
    """
    action: str = "grading-callback"
    submission_id: str
    grading_result: GradingResult


# ============= Health Check =============

class HealthResponse(BaseModel):
    """Response from GET /health"""
    status: str = "healthy"
    version: str = "1.0.0"
    redis_connected: bool
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
