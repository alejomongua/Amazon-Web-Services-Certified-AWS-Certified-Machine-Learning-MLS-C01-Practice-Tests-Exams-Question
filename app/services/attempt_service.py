import random
import json
import datetime
from flask import session
from app import db
from app.models import Question, Attempt


def get_or_create_attempt():
    """
    Retrieve the current attempt from session.
    If none exists, create a new one.
    """
    attempt_id = session.get("attempt_id")
    if attempt_id:
        attempt = Attempt.query.get(attempt_id)
        if attempt:
            return attempt

    # Create a new attempt.
    question_ids = [q.id for q in Question.query.all()]
    random.shuffle(question_ids)
    attempt = Attempt(
        question_order=json.dumps(question_ids),
        start_time=datetime.datetime.utcnow()
    )
    db.session.add(attempt)
    db.session.commit()
    session["attempt_id"] = attempt.id
    return attempt


def update_attempt_end_time(attempt):
    """Mark the attempt as finished."""
    attempt.end_time = datetime.datetime.now(datetime.timezone.utc)
    db.session.commit()
