from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load API keys from environment
groq_api_key = os.getenv("GROQ_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")

print("Pinecone API Key:", pinecone_api_key)  # Debug line

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)

# Initialize embeddings for document retrieval
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Check if index exists, if not create it
index_name = "wellmate-chatbot"
dimension = 384  # all-MiniLM-L6-v2 uses 384 dimensions

if index_name not in pc.list_indexes().names():
    print(f"Creating new index: {index_name}")
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric='cosine',
        spec=ServerlessSpec(
            cloud='aws',
            region='us-west-2'
        )
    )

# Connect to Pinecone vector store
docsearch = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embeddings)
retriever = docsearch.as_retriever(search_kwargs={"k": 1})

# Initialize Grok LLM
llm = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile", temperature=0.2, max_tokens=200)

# Prompt to contextualize questions based on chat history
contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question that can be understood "
    "without the chat history. Do NOT answer it, just reformulate if needed."
)
contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [("system", contextualize_q_system_prompt), MessagesPlaceholder("chat_history"), ("human", "{input}")]
)
history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

# Constraints on responses (e.g., sentence limit, banned phrases)
def enforce_constraints(response, chat_history, user_input):
    bot_response = response['answer']
    # Limit to 4 sentences
    sentences = [s.strip() for s in bot_response.split('.') if s.strip()]
    if len(sentences) > 4:
        bot_response = '. '.join(sentences[:4]) + '.'
    
    # Prevent premature prescriptions
    if "prescribe" in bot_response.lower() and len(chat_history.messages) < 4:
        bot_response = "I need more details about your condition before prescribing anything. What symptoms are you experiencing?"
    
    # Ban phrases
    banned_phrases = ["Sorry to hear", "I cannot help", "I am not a doctor", "I'm glad you reached out"]
    if any(phrase in bot_response.lower() for phrase in banned_phrases):
        bot_response = "Let me assist you. What can I help you with today? 😊"
    
    # Handle name introduction
    name_asked = "who are you" in user_input.lower() or "name" in user_input.lower()
    if name_asked and "dr." not in bot_response.lower():
        bot_response = f"My name is Dr. Black 😊. I'm a physician with 30 years of experience. How can I assist you today? What symptoms are you experiencing?"
    elif not name_asked and "dr. black" in bot_response.lower():
        bot_response = bot_response.replace("Dr. Black", "me").replace("dr. black", "me")
    elif name_asked and "dr." in bot_response.lower() and "dr. black" not in bot_response.lower():
        bot_response = bot_response.replace("Dr. Smith", "Dr. Black").replace("dr. smith", "dr. black")

    return bot_response

# Generate chatbot response
def generate_response(system_prompt, chat_history, user_input, max_history=10):
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), MessagesPlaceholder("chat_history"), ("human", "{input}")]
    )
    
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=prompt,
        document_variable_name="context"
    )
    
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    response = rag_chain.invoke({"input": user_input, "chat_history": chat_history.messages})
    bot_response = enforce_constraints(response, chat_history, user_input)
    
    chat_history.add_user_message(user_input)
    chat_history.add_ai_message(bot_response)
    if len(chat_history.messages) > max_history:
        chat_history.messages = chat_history.messages[-max_history:]
    
    return bot_response