# langchain_hello.py — my first LangChain call
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()  # reads OPENAI_API_KEY from your .env, same as before

# ChatOpenAI is LangChain's wrapper around the OpenAI API.
# Think of it as a stand-in for your llm_client.py.
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# You send a LIST of (role, content) messages — the same
# system/user roles you learned in the chatbot lab.
response = llm.invoke([
    ("system", "You are a terse assistant."),
    ("human", "In one sentence, what is a unit test?"),
])

# .invoke() returns a message OBJECT; the text lives on .content
print(response.content)