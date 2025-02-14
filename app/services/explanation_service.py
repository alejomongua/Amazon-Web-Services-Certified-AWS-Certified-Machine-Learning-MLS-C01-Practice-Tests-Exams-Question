import os
from dotenv import load_dotenv

# Import Gemini from LangChain (assuming LangChain supports Gemini similarly to OpenAI)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Build a prompt template for the LLM
PROMPT_TEMPLATE = (
    "You are an expert on machine learning, you are also an expert in AWS, AWS best practices and AWS quiz questions. "
    "Please provide a detailed explanation for the following question:\n\n"
    "Question: {question_text}\n\n"
    "Correct Answer(s):\n{correct_answers}\n\n"
    "Distractors:\n{distractors}\n\n"
    "Provide a clear explanation on why the correct answer(s) is correct and why the distractors are incorrect and explain key concepts. "
    "There is a small chance that the answer given as correct is wrong, you, as an expert, should correct it in that case and argument very well your reasoning."
)


def generate_explanation(question_text, correct, distractors):
    prompt = PromptTemplate(
        input_variables=["question_text", "correct_answers", "distractors"],
        template=PROMPT_TEMPLATE
    )
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.7,
        api_key=os.environ.get("GOOGLE_API_KEY")
    )
    chain = prompt | llm
    result = chain.invoke({
        "question_text": question_text,
        "correct_answers": "\n".join(correct),
        "distractors": "\n".join(distractors)
    })
    if hasattr(result, "content"):
        return result.content
    return str(result)
