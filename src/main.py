from pyexpat import model
import streamlit as st
import json
import re
import os
import boto3
from langchain.llms.bedrock import Bedrock
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

os.environ["AWS_PROFILE"] = "sso-bedrock"

# creating the bedrock client
client = boto3.client('bedrock-runtime', region_name="eu-central-1")
model_name = "anthropic.claude-v2"


# setting up the llm_model to use the anthropic.claude-v2 model from bedrock, plus model_kwargs to use when hitting the bedrock api
llm_model = Bedrock(
    model_id=model_name, 
    client=client,
    model_kwargs={"max_tokens_to_sample": 2000, "temperature": 0.5}
    )

# defining the test_bot function that takes in the language and text and returns the response
# the template defines content that will be added to all user input promps
def test_bot(language, text):
    prompt = PromptTemplate(
        input_variables=["language", "text"],
        template="""
        You are a helpful assistant.
        {language}
        Human: {text}
        Assistant:""",
    )
    # now we to define the LLMChain, which is a class that takes in the llm model and the prompt
    chain = LLMChain(
        llm=llm_model, 
        prompt=prompt
    )
    response = chain({"language": language, "text": text})
    return response

# testing when running $ python main.py
# print(test_bot("Engish", "Hello, how long is the longest river in the world?"))

# defining the strealit app
def main():
    st.title("Q&A with Anthropic.claude-v2")
    language = st.selectbox("Select a language", ["English", "German", "French", "Spanish"])
    text = st.text_input("Enter your text")
    if st.button("Submit"):
        response = test_bot(language, text)
        st.write(response["text"])

def main2():
    st.title("ChatBot with Anthropic.claude-v2")
    language = st.selectbox("Select a language", ["English", "German", "French", "Spanish"])
    text = st.chat_input("Say something")
    if text:
        response = test_bot(language, text)
        st.write(f"The user has sent {response}")


if __name__ == "__main__":
    main()

## run as 
## python -m streamlit run main.py --theme.primaryColor "#ffffff"