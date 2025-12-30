def print_grading_report(response):
    import json

    data = None

    for output_item in response.output:
        if output_item.type == "message":
            for content_item in output_item.content:
                if content_item.type == "output_text":
                    data = json.loads(content_item.text)
                    break

    if data is None:
        print("❌ No grading JSON found")
        return

    print("\n=== OVERALL SCORE ===")
    s = data["overall_score"]
    print(f'{s["obtained"]}/{s["maximum"]} ({s["percentage"]}%)')

    print("\n=== RUBRIC BREAKDOWN ===")
    for r in data["rubric_breakdown"]:
        print(f'\n• {r["criterion"].upper()}')
        print(f'  Score: {r["awarded_marks"]}/{r["max_marks"]}')
        print(f'  Evaluation: {r["evaluation"]}')
        for gap in r.get("student_gaps", []):
            print(f'   - {gap}')

    print("\n=== FINAL VERDICT ===")
    v = data["final_verdict"]
    print(f'Grade: {v["grade"]}')
    print(f'Summary: {v["summary"]}')

    print("\n=== ACTIONABLE FEEDBACK ===")
    for f in data["actionable_feedback"]:
        print(f'• {f}')
