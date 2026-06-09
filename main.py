
from anthropic import Anthropic,AnthropicError
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MAX_QUESTIONS = 3



SYSTEM_PROMPT = """You are a helpful assistant that answers questions about the world. 
                   You have access to a large amount of information and can provide 
                   detailed and accurate answers to any question. You are also able to 
                   provide sources for your answers when possible. Give at most a two sentence summary"""

def conversation():
    message_memory = []
    question_count: int = 0    

    while True:     
        human_prompt = input("You? ").strip()                     
        if human_prompt.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        
        if question_count >= MAX_QUESTIONS:
            print("\nMaximum number of questions per conversation reached")
            print("Goodbye!")
            break

        question_count += 1               
       
        try:
            message = client.messages.create(
                system=SYSTEM_PROMPT,    
                max_tokens=1024,
                model="claude-haiku-4-5-20251001",
                messages = message_memory
            )
            reply = message.content[0].text
            print("Answer:")
            print(reply)
            message_memory.append({ "role": "user", "content": human_prompt })
            message_memory.append({ "role": "assistant", "content": reply })
            print("\n\n")
        except AnthropicError as e:
            print(e)      


if __name__ == "__main__":
    conversation()

