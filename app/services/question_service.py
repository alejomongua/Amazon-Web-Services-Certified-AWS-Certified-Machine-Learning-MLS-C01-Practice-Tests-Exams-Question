import json

from flask import session
from app.models import Question, Attempt, AttemptAnswer


def get_question_and_answers(qid):
    """
    Helper function to retrieve the question and corresponding attempt answer.
    Returns a tuple with:
        - question object
        - selected answers (list of texts)
        - correct answers (list of texts)
        - attempt_answer object
        - attempt_id
    """
    attempt_id = session.get("attempt_id")
    if not attempt_id:
        return None, None, None, None, attempt_id  # Return early if no attempt

    q = Question.query.get(qid)
    if not q:
        return None, None, None, None, attempt_id  # Return early if question not found

    attempt_answer = AttemptAnswer.query.filter_by(
        attempt_id=attempt_id, question_id=q.id).first()
    if not attempt_answer:
        return None, None, None, None, attempt_id  # Return early if no attempt answer

    # Get selected answer texts and correct answer texts
    try:
        selected_ids = set(json.loads(attempt_answer.selected_answers))
    except Exception:
        selected_ids = set()
    selected_texts = [ans.text for ans in q.answers if ans.id in selected_ids]
    correct_texts = [ans.text for ans in q.answers if ans.is_correct]

    return q, selected_texts, correct_texts, attempt_answer


def get_correct_incorrect_count(attempt_id):
    if not attempt_id:
        return 0, 0
    attempt = Attempt.query.get(attempt_id)
    if not attempt:
        return 0, 0
    correct_count = sum(
        1 for aa in attempt.attempt_answers if aa.is_correct)
    incorrect_count = len(attempt.attempt_answers) - correct_count
    return correct_count, incorrect_count
