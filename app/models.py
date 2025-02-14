import datetime
import json
from app import db


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)
    image = db.Column(db.String, nullable=True)
    # One-to-many: A question can have many answer options.
    answers = db.relationship("Answer", backref="question", lazy=True)
    explanation = db.Column(db.String, nullable=True)


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    question_id = db.Column(db.Integer, db.ForeignKey(
        "question.id"), nullable=False)


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(
        db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    end_time = db.Column(db.DateTime, nullable=True)
    # The order of questions is stored as a JSON list of question IDs
    question_order = db.Column(db.Text, nullable=False)
    # Relationship to all answers submitted during the attempt
    attempt_answers = db.relationship(
        "AttemptAnswer", backref="attempt", lazy=True)

    @property
    def questions(self):
        """Return the parsed list of question IDs from question_order."""
        try:
            return json.loads(self.question_order)
        except (ValueError, TypeError):
            return []

    def get_remaining_question_ids(self):
        """Return the list of question IDs that have not yet been answered."""
        answered_q_ids = {aa.question_id for aa in self.attempt_answers}
        return [qid for qid in self.questions if qid not in answered_q_ids]

    def calculate_scores(self):
        """Calculate the number of correct and incorrect answers."""
        correct_count = sum(1 for aa in self.attempt_answers if aa.is_correct)
        incorrect_count = len(self.attempt_answers) - correct_count
        return correct_count, incorrect_count

    @property
    def correct_percentage(self):
        """Return the percentage of correct answers (if any answers exist)."""
        total = len(self.attempt_answers)
        if total == 0:
            return 0
        correct_count, _ = self.calculate_scores()
        return (correct_count / total) * 100


class AttemptAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey(
        "attempt.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey(
        "question.id"), nullable=False)
    # Store the selected answer IDs as a JSON list (e.g. "[1, 4]" )
    selected_answers = db.Column(db.Text, nullable=False)
    # Store the date and time when the answer was submitted
    submission_time = db.Column(
        db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # Set up a relationship to access the question from the answer record.
    question = db.relationship(
        "Question", backref="attempt_answers", lazy=True)

    @property
    def is_correct(self):
        """Compute if the selected answers match exactly the correct answers."""
        try:
            selected = set(json.loads(self.selected_answers))
        except Exception:
            selected = set()
        correct_ids = {
            ans.id for ans in self.question.answers if ans.is_correct}
        return selected == correct_ids
