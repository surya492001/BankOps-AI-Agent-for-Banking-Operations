from app.llm.client import llm


response = llm.invoke(
    "Explain what a P1 banking incident means in one sentence."
)


print(response.content)
