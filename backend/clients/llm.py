import os

from langchain_openai import ChatOpenAI


def get_chat_model():
    api_key = os.getenv("OPENAI_API_KEY", "")
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    chat_model = ChatOpenAI(
        model_name=model_name, temperature=temperature, api_key=api_key
    )

    return chat_model


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv()
    chat_model = get_chat_model()

    print(chat_model.invoke("hello, world!").content)
