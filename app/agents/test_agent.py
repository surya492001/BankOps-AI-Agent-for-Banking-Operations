from app.agents.graph import ask_agent


question = """
Investigate INC-1044 and recommend the appropriate operational response.
"""


response = ask_agent(question)


print("\n==============================")
print("BANKOPS AI RESPONSE")
print("==============================\n")

print(response)
