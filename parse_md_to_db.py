import re
from app import create_app, db
from app.models import Question, Answer

app = create_app()
app.app_context().push()


def parse_markdown_file(file_path):
    """
    Parses the Markdown file into a list of dictionaries.
    Each dictionary has: 'question', optional 'image', 'answers', and 'correct_answers' (list of indices).
    """
    questions_data = []
    current_question = None
    current_image = None
    answers = []
    correct_answers = []

    # Patterns for answers and images.
    answer_pattern = re.compile(r'^-\s*\[(x| )\]\s*(.*)$')
    image_pattern = re.compile(r'^!\[.*?\]\((.*?)\)')

    with open(file_path, 'r', encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if line.startswith("### "):
            # Save previous question if it exists
            if current_question is not None and answers:
                questions_data.append({
                    'question': current_question,
                    'image': current_image,
                    'answers': answers,
                    'correct_answers': correct_answers
                })
            current_question = line[4:].strip()
            current_image = None
            answers = []
            correct_answers = []
        else:
            # Check for an image line. The image file is expected to be in the "images" folder.
            image_match = image_pattern.match(line)
            if image_match:
                # Store the relative path (e.g., "question1.jpg")
                current_image = image_match.group(1)
            else:
                # Check for answer options.
                match = answer_pattern.match(line)
                if match:
                    answer_text = match.group(2).strip()
                    answers.append(answer_text)
                    if match.group(1).lower() == "x":
                        correct_answers.append(len(answers) - 1)
    if current_question is not None and answers:
        questions_data.append({
            'question': current_question,
            'image': current_image,
            'answers': answers,
            'correct_answers': correct_answers
        })
    return questions_data


def populate_db_from_md(md_file):
    questions_data = parse_markdown_file(md_file)

    # Optionally, clear existing questions:
    # from app.models import Answer, Question
    # db.session.query(Answer).delete()
    # db.session.query(Question).delete()
    # db.session.commit()

    for q in questions_data:
        # Check if question with that text already exists
        question = Question.query.filter_by(text=q["question"]).first()
        if question:
            # print(
            #     f"Question '{q['question']}' already exists in the database.")
            continue
        new_question = Question(text=q["question"], image=q.get("image"))
        db.session.add(new_question)
        db.session.commit()  # To generate an ID for the question.
        for idx, ans_text in enumerate(q["answers"]):
            is_correct = idx in q["correct_answers"]
            new_answer = Answer(
                text=ans_text, is_correct=is_correct, question_id=new_question.id)
            db.session.add(new_answer)
        db.session.commit()
    print(
        f"Database populated with {len(questions_data)} questions from '{md_file}'.")


if __name__ == '__main__':
    # The questions file is README.md in the project root.
    md_file = "README.md"
    populate_db_from_md(md_file)
