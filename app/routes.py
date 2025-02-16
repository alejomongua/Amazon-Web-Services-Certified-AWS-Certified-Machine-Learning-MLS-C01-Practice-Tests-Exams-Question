import random
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
from app.services.question_service import get_question_and_answers
from app.services.attempt_service import get_or_create_attempt, update_attempt_end_time

main = Blueprint('main', __name__)


@main.route("/", methods=["GET"])
def quiz():
    # Get or create the attempt.
    attempt = get_or_create_attempt()

    # Use the model methods for score and remaining questions.
    correct_count, incorrect_count = attempt.calculate_scores()
    total_questions = len(attempt.questions)
    remaining_qids = attempt.get_remaining_question_ids()

    if not remaining_qids:
        update_attempt_end_time(attempt)
        return redirect(url_for("main.history"))

    current_question_id = remaining_qids[0]
    q = Question.query.get(current_question_id)

    # Shuffle answers for display.
    shuffled_answers = random.sample(q.answers, len(q.answers))

    # Store the shuffled order and current question in session.
    session["current_shuffled_answer_ids"] = [a.id for a in shuffled_answers]
    session["current_question_id"] = q.id

    # Check if question accepts more than one answer.
    multiple_answers = len([a for a in q.answers if a.is_correct]) > 1

    return render_template(
        "quiz.html",
        question=q.text,
        answers=[a.text for a in shuffled_answers],
        answer_indices=range(len(shuffled_answers)),
        answered=False,
        image=q.image,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        total_questions=total_questions,
        multiple_answers=multiple_answers,
        correct_percentage=attempt.correct_percentage
    )


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
    q, selected_texts, correct_texts, attempt_answer = get_question_and_answers(
        qid)

    attempt = get_or_create_attempt()

    correct_count, incorrect_count = attempt.calculate_scores()
    total_questions = len(attempt.questions)

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
        total_questions=total_questions,
        image=q.image,
    )


@main.route("/explain/<int:qid>")
def explain(qid):
    # Retrieve question and related data using your helper function.
    q, selected_texts, correct_texts, attempt_answer = get_question_and_answers(
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
            q.text, correct_texts, distractors, q.image)

        # Save the explanation in the question record to avoid future LLM calls.
        q.explanation = explanation_markdown
        db.session.commit()

    # Convert markdown to HTML.
    explanation_html = Markup(markdown.markdown(explanation_markdown))

    return render_template(
        "explanation.html",
        explanation=explanation_html,
        image=q.image,
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

    answered_questions = []
    if current_attempt:
        # Assuming each AttemptAnswer has a relationship to the Question via .question
        answered_questions = current_attempt.attempt_answers
    return render_template(
        "history.html",
        attempts=attempts,
        current_attempt=current_attempt,
        answered_questions=answered_questions
    )
