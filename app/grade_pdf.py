import os
import dotenv
from openai import OpenAI
from prompt_gen import build_grading_prompt
from parse_pdfs import extract_text_from_pdf
from pretty_json import print_grading_report
dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def grade_pdf(teacher_pdf: str, student_pdf: str, assignment_metadata: dict, grading_rubric : dict) -> dict:
    teacher_solution = extract_text_from_pdf(teacher_pdf)
    student_solution = extract_text_from_pdf(student_pdf)

    client = OpenAI()

    response = client.responses.create(
        model="gpt-5-nano",
        input= build_grading_prompt(assignment_metadata, grading_rubric, teacher_solution, student_solution),
    )
    return response


teacher_pdf = "/Users/mukund604/Documents/GitHub/graderight-academic-suite/python-grader/sample-pdfs/teacher.pdf"
student_pdf = "/Users/mukund604/Documents/GitHub/graderight-academic-suite/python-grader/sample-pdfs/student.pdf"
assignment_metadata = {
    "assignment_id": "CS101_HW3_Q2",
    "course_name": "Introduction to Machine Learning",
    "topic": "Linear Regression",
    "difficulty_level": "medium",
    "expected_length": "1-2 pages"
}
grading_rubric = {
    "total_marks": 100,
    "criteria": {
        "concept_coverage": {
            "weight": 30,
            "description": "Coverage of required theoretical concepts",
            "levels": {
                "excellent": {
                    "score_range": [26, 30],
                    "description": "All core concepts are correctly identified and explained"
                },
                "good": {
                    "score_range": [20, 25],
                    "description": "Most concepts covered with minor gaps"
                },
                "partial": {
                    "score_range": [10, 19],
                    "description": "Some important concepts missing or unclear"
                },
                "poor": {
                    "score_range": [0, 9],
                    "description": "Major conceptual misunderstandings"
                }
            }
        },
        "reasoning_quality": {
            "weight": 25,
            "description": "Logical flow and soundness of reasoning",
            "levels": {
                "excellent": {
                    "score_range": [21, 25],
                    "description": "Clear, coherent, step-by-step reasoning"
                },
                "good": {
                    "score_range": [16, 20],
                    "description": "Mostly logical with minor inconsistencies"
                },
                "partial": {
                    "score_range": [8, 15],
                    "description": "Weak or fragmented reasoning"
                },
                "poor": {
                    "score_range": [0, 7],
                    "description": "Illogical or unsupported arguments"
                }
            }
        },
        "correctness": {
            "weight": 30,
            "description": "Accuracy of facts, equations, and conclusions",
            "levels": {
                "excellent": {
                    "score_range": [26, 30],
                    "description": "All derivations and statements are correct"
                },
                "good": {
                    "score_range": [20, 25],
                    "description": "Minor computational or factual errors"
                },
                "partial": {
                    "score_range": [10, 19],
                    "description": "Multiple errors affecting correctness"
                },
                "poor": {
                    "score_range": [0, 9],
                    "description": "Mostly incorrect or invalid solution"
                }
            }
        },
        "clarity": {
            "weight": 15,
            "description": "Clarity, structure, and presentation",
            "levels": {
                "excellent": {
                    "score_range": [13, 15],
                    "description": "Well-structured, clear, and easy to follow"
                },
                "good": {
                    "score_range": [10, 12],
                    "description": "Understandable but slightly messy"
                },
                "partial": {
                    "score_range": [5, 9],
                    "description": "Hard to follow"
                },
                "poor": {
                    "score_range": [0, 4],
                    "description": "Unclear or poorly presented"
                }
            }
        }
    }
}
response = grade_pdf(student_pdf, teacher_pdf, grading_rubric, assignment_metadata)
print(response)
print_grading_report(response)
