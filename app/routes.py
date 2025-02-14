import random
import datetime
import json
import markdown

from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
)
from markupsafe import Markup
from app import db
from app.models import Question, Attempt, AttemptAnswer
from app.services.explanation_service import generate_explanation

main = Blueprint('main', __name__)


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

    return q, selected_texts, correct_texts, attempt_answer, attempt_id


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


@main.route("/", methods=["GET"])
def quiz():
    # Ensure an attempt exists
    attempt_id = session.get("attempt_id")
    attempt = Attempt.query.get(attempt_id) if attempt_id else None
    if not attempt:
        question_ids = [q.id for q in Question.query.all()]
        random.shuffle(question_ids)
        attempt = Attempt(question_order=json.dumps(question_ids))
        db.session.add(attempt)
        db.session.commit()
        session["attempt_id"] = attempt.id

    correct_count, incorrect_count = get_correct_incorrect_count(attempt.id)

    # Determine current question (first unanswered in the order)
    question_order = json.loads(attempt.question_order)
    answered_q_ids = {aa.question_id for aa in attempt.attempt_answers}
    remaining_qids = [
        qid for qid in question_order if qid not in answered_q_ids]
    if not remaining_qids:
        attempt.end_time = datetime.datetime.utcnow()
        db.session.commit()
        return redirect(url_for("main.history"))
    current_question_id = remaining_qids[0]
    q = Question.query.get(current_question_id)
    # Shuffle answers for display
    shuffled_answers = random.sample(q.answers, len(q.answers))

    # Store the shuffled order in session to be used when processing the submission.
    session["current_shuffled_answer_ids"] = [a.id for a in shuffled_answers]
    session["current_question_id"] = q.id

    # Check if question accepts more than one answer
    multiple_answers = len([a for a in q.answers if a.is_correct]) > 1

    # Render the question view (if not answered yet)
    return render_template("quiz.html",
                           question=q.text,
                           answers=[a.text for a in shuffled_answers],
                           answer_indices=range(len(shuffled_answers)),
                           answered=False,
                           image=q.image,
                           correct_count=correct_count,
                           incorrect_count=incorrect_count,
                           multiple_answers=multiple_answers,
                           correct_percentage=attempt.correct_percentage)


@main.route("/submit_answer", methods=["POST"])
def submit_answer():
    attempt_id = session.get("attempt_id")
    if not attempt_id:
        return redirect(url_for("main.quiz"))
    attempt = Attempt.query.get(attempt_id)
    current_qid = session.get("current_question_id")
    if not current_qid:
        return redirect(url_for("main.quiz"))
    q = Question.query.get(current_qid)

    # Retrieve the shuffled answer order from session
    shuffled_answer_ids = session.get("current_shuffled_answer_ids")
    if not shuffled_answer_ids:
        return redirect(url_for("main.quiz"))

    # Process submitted answers (checkbox values correspond to indices in the shuffled order)
    selected = request.form.getlist("answer")
    try:
        selected_indices = [int(x) for x in selected]
        # Map indices to actual answer IDs
        selected_answer_ids = [shuffled_answer_ids[i]
                               for i in selected_indices]
    except Exception:
        selected_answer_ids = []

    # Check if this question was already answered; if not, record the answer.
    attempt_answer = AttemptAnswer.query.filter_by(
        attempt_id=attempt.id, question_id=q.id).first()
    if not attempt_answer:
        attempt_answer = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            selected_answers=json.dumps(selected_answer_ids)
        )
        db.session.add(attempt_answer)
        db.session.commit()

    # Redirect to a route that shows the answered view.
    return redirect(url_for("main.answered_view", qid=q.id))


@main.route("/answered/<int:qid>", methods=["GET"])
def answered_view(qid):
    q, selected_texts, correct_texts, attempt_answer, attempt_id = get_question_and_answers(
        qid)

    correct_count, incorrect_count = get_correct_incorrect_count(attempt_id)

    # If no valid attempt or question, redirect to quiz
    if not q or not attempt_answer:
        return redirect(url_for("main.quiz"))

    return render_template(
        "quiz.html",
        question=q.text,
        qid=qid,
        answered=True,
        selected_answers=selected_texts,
        correct_answers=correct_texts,
        all_answers=q.answers,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        image=q.image,
    )


@main.route("/explain/<int:qid>")
def explain(qid):
    # Retrieve question and related data using your helper function.
    q, selected_texts, correct_texts, attempt_answer, _ = get_question_and_answers(
        qid)

    # If no valid attempt or question, redirect to quiz.
    if not q or not attempt_answer:
        return redirect(url_for("main.quiz"))

    # If the explanation is already saved in the question record, use it.
    if q.explanation:
        explanation_markdown = q.explanation
    else:
        distractors = [
            ans.text for ans in q.answers if ans.text not in correct_texts]
        explanation_markdown = generate_explanation(
            q.text, correct_texts, distractors)

        # Save the explanation in the question record to avoid future LLM calls.
        q.explanation = explanation_markdown
        db.session.commit()

    # Convert markdown to HTML.
    explanation_html = Markup(markdown.markdown(explanation_markdown))

    return render_template(
        "explanation.html",
        explanation=explanation_html,
        question=q.text,
        selected_answers=selected_texts,
        correct_answers=correct_texts,
        all_answers=q.answers
    )


@main.route("/next")
def next_question():
    return redirect(url_for("main.quiz"))


@main.route("/reset")
def reset_quiz():
    session.pop("attempt_id", None)
    return redirect(url_for("main.quiz"))


@main.route("/history")
def history():
    attempts = Attempt.query.order_by(Attempt.start_time.desc()).all()
    current_attempt_id = session.get("attempt_id")
    current_attempt = Attempt.query.get(current_attempt_id
                                        ) if current_attempt_id else None
    return render_template("history.html", attempts=attempts, current_attempt=current_attempt)
