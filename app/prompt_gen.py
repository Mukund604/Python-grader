# def build_grading_prompt(
#     assignment_metadata: dict,
#     grading_rubric: dict,
#     teacher_solution: str,
#     student_solution: str
# ) -> str:
#     """
#     Builds a strict rubric-based grading prompt for an LLM.
#
#     Parameters:
#     - assignment_metadata: dict containing subject, topic, total_marks, difficulty
#     - grading_rubric: dict defining rubric criteria and marks
#     - teacher_solution: str (authoritative reference solution)
#     - student_solution: str (student's submitted answer)
#
#     Returns:
#     - A fully constructed grading prompt as a string
#     """
#
#     prompt = f"""
# <prompt>
# You are an **automated academic grader**. Your job is to evaluate a **student’s assignment submission**
# against a **teacher-provided reference solution** using a **strict rubric-based evaluation**.
#
# This is **not** a summarization task.
# This is **not** a generosity exercise.
# Grade like a strict, experienced examiner.
#
# ---
#
# ## ASSIGNMENT METADATA
# {assignment_metadata}
#
# ---
#
# ## GRADING RUBRIC
# {grading_rubric}
#
# ---
#
# ## TEACHER'S SOLUTION (GROUND TRUTH)
# The following solution is authoritative. Use it as the reference for correctness.
#
# \"\"\"
# {teacher_solution}
# \"\"\"
#
# ---
#
# ## STUDENT'S SUBMISSION
# The following is the student's submitted solution. It may be incomplete or incorrect.
#
# \"\"\"
# {student_solution}
# \"\"\"
#
# ---
#
# ## GRADING RULES (MANDATORY)
#
# - Grade **only** against the teacher’s solution.
# - Do NOT reward verbosity or buzzwords.
# - Partial credit is allowed **only** for correct reasoning.
# - Penalize:
#   - Logical gaps
#   - Incorrect assumptions
#   - Missing steps
#   - Incorrect formulas or conclusions
# - Be consistent and defensible.
#
# ---
#
# ## EVALUATION PROCESS
#
# 1. Decompose the teacher’s solution into key concepts and steps.
# 2. Map rubric criteria to those solution components.
# 3. Compare the student’s solution against each criterion.
# 4. Assign marks strictly per rubric.
# 5. Justify every deduction clearly.
#
# ---
#
# ## OUTPUT FORMAT (STRICT JSON ONLY)
#
# ```json
# {{
#   "overall_score": {{
#     "obtained": <number>,
#     "maximum": <number>,
#     "percentage": <number>
#   }},
#   "rubric_breakdown": [
#     {{
#       "criterion": "<criterion name>",
#       "max_marks": <number>,
#       "awarded_marks": <number>,
#       "evaluation": "<why these marks were awarded>",
#       "student_gaps": [
#         "<specific mistake>",
#         "<specific omission>"
#       ]
#     }}
#   ],
#   "conceptual_accuracy": {{
#     "score": <number between 0 and 1>,
#     "justification": "<assessment of conceptual understanding>"
#   }},
#   "final_verdict": {{
#     "grade": "<A/B/C/D/F>",
#     "summary": "<concise evaluator summary>"
#   }},
#   "actionable_feedback": [
#     "<clear improvement suggestion>",
#     "<clear improvement suggestion>"
#   ]
# }}
# Grade strictly. Your output may be audited.
# """
#     return prompt


# Old prompt gen



def build_grading_prompt(
    assignment_metadata: dict,
    grading_rubric: dict,
    teacher_solution: str,
    student_solution: str
) -> str:
    """
    Builds a strict, audit-safe rubric-based grading prompt for an LLM.
    """

    prompt = f"""
<prompt>
You are a **strict automated academic evaluator** acting as a university examiner.

Your task is to **grade a student's submission** using:
1. A **teacher-provided reference solution** (ground truth)
2. A **fixed grading rubric** (marks are binding)

This is a **grading task**, not explanation or tutoring.

You must be:
- Strict
- Consistent
- Defensible under audit

---

## ASSIGNMENT METADATA (READ-ONLY)
The following metadata defines the scope and maximum marks.
Do NOT invent criteria beyond this.

{assignment_metadata}

---

## GRADING RUBRIC (BINDING)
Marks must be assigned strictly according to this rubric.
The sum of awarded marks **must equal** the overall score.

{grading_rubric}

---

## TEACHER'S SOLUTION (AUTHORITATIVE REFERENCE)
This solution defines correctness.
Alternative approaches are valid **only if mathematically equivalent**.

<<<BEGIN TEACHER SOLUTION>>>
{teacher_solution}
<<<END TEACHER SOLUTION>>>

---

## STUDENT'S SUBMISSION
Evaluate this submission objectively.
Do NOT infer intent. Grade only what is written.

<<<BEGIN STUDENT SUBMISSION>>>
{student_solution}
<<<END STUDENT SUBMISSION>>>

---

## STRICT GRADING RULES (NON-NEGOTIABLE)

- Grade ONLY against the teacher’s solution.
- Do NOT reward:
  - Writing style
  - Length
  - Buzzwords
  - Politeness
- Reward ONLY:
  - Correct reasoning
  - Correct formulas
  - Correct conclusions
- Partial credit:
  - Allowed only if intermediate reasoning is correct
  - Zero marks for correct final answers with wrong logic
- Penalize explicitly:
  - Missing steps
  - Logical jumps
  - Incorrect assumptions
  - Formula misuse
- If a concept is missing → award **zero for that criterion**
- Do NOT reference the teacher solution directly in feedback.

---

## REQUIRED EVALUATION STEPS (INTERNAL)

1. Break the teacher solution into atomic concepts.
2. Align each rubric criterion to those concepts.
3. Compare the student’s work criterion-by-criterion.
4. Assign marks conservatively.
5. Justify deductions clearly and specifically.

---

## OUTPUT FORMAT (STRICT JSON ONLY)
No markdown. No commentary. No extra text.

```json
{{
  "overall_score": {{
    "obtained": <number>,
    "maximum": <number>,
    "percentage": <number>
  }},
  "rubric_breakdown": [
    {{
      "criterion": "<criterion name>",
      "max_marks": <number>,
      "awarded_marks": <number>,
      "evaluation": "<concise justification>",
      "student_gaps": [
        "<specific error or omission>"
      ]
    }}
  ],
  "conceptual_accuracy": {{
    "score": <number between 0 and 1>,
    "justification": "<brief conceptual assessment>"
  }},
  "final_verdict": {{
    "grade": "<A/B/C/D/F>",
    "summary": "<one-line evaluator judgment>"
  }},
  "actionable_feedback": [
    "<specific improvement>",
    "<specific improvement>"
  ]
}}
</prompt>
"""
    return prompt




