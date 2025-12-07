from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
from modules.db import add_user, add_conversation, add_history, add_history_rate, get_conversations_by_user, get_history, revoke_refresh_token
from peft import PeftModel
import torch
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage
from modules.models import Message, UserCreate, LoginRequest, HistoryRate, RefreshRequest
from fastapi import FastAPI, Depends, HTTPException, Body
from modules.security import login_user, require_role, new_access_token
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
import os
import yaml
from langdetect import detect
import uvicorn


with open("LLM-config.yml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

lora_checkpoint_path = config["lora_checkpoint_path"]
model_name = config["model_name"]
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

if torch.cuda.is_available():
    device_map = "auto"
    dtype = torch.bfloat16

else:
    device_map = "cpu"
    dtype = torch.float16

base_model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map=device_map,
    dtype= dtype
)

model = PeftModel.from_pretrained(base_model, lora_checkpoint_path)
pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map=device_map)

def generate_response(userinput, conversationid):
    if config["history_length"] == "max":
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    else:
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, k=config["history_length"])

    history = get_history(conversationid)
    for row in history:
        memory.chat_memory.add_message(HumanMessage(content=row["usermessage"]))
        memory.chat_memory.add_message(AIMessage(content=row["llmmessage"]))

    chathistorytext = ""
    for m in memory.load_memory_variables({})["chat_history"]:
        historylang = detect(m.content)
        if historylang == "pl":
            if m.type == "human":
                chathistorytext += f"Użytkownik: {m.content}\n"
            else:
                chathistorytext += f"Asystent: {m.content}\n"
        else:
            if m.type == "human":
                chathistorytext += f"User: {m.content}\n"
            else:
                chathistorytext += f"Assistant: {m.content}\n"

    lang = detect(userinput)
    if lang == "pl":
        system_prompt = config["system_prompt_pl"]
        prompt = (
            f"{system_prompt}\n"
            f"{chathistorytext}"
            f"Użytkownik: {userinput}\n"
            f"Asystent:"
        )
    else:
        system_prompt = config["system_prompt_en"]
        prompt = (
            f"{system_prompt}\n"
            f"{chathistorytext}"
            f"User: {userinput}\n"
            f"Assistant:"
        )
    output = pipe(
        prompt,
        max_new_tokens=config["max_new_tokens"],
        do_sample=config["do_sample"],
        temperature=config["temperature"],
        top_p=config["top_p"],
        repetition_penalty=config["repetition_penalty"],
        eos_token_id=tokenizer.eos_token_id
    )

    generatedtext = output[0]["generated_text"]

    if "Asystent:" in generatedtext:
        assistantreply = generatedtext.split("Asystent:")[-1]
    else:
        assistantreply = generatedtext

    if "Użytkownik:" in assistantreply:
        assistantreply = assistantreply.split("Użytkownik:")[0]

    reply = assistantreply.strip()

    del memory

    return reply

print("Rozpoczynam rozmowę z Asystentem.")



@app.post("/users/new")
def create_user(user: UserCreate, auth=Depends(require_role(["admin"]))):

    newuserid = add_user(
        name=user.name,
        surname=user.surname,
        login=user.login,
        mail=user.mail,
        password=user.password
    )
    if newuserid is None:
        return {"detail": "User exist in database"}
    return {"user_id": newuserid}

@app.post("/login")
def login_endpoint(credentials: LoginRequest):
    token = login_user(credentials.login, credentials.password)
    return {"result": token}

@app.post("/conversations/new")
def create_conversation(auth=Depends(require_role(["admin", "user"]))):
    userid = auth["user_id"]
    convid = add_conversation(userid)
    return {"conversation_id": convid}

@app.get("/conversations")
def get_conversations(auth=Depends(require_role(["admin", "user"]))):
    userid = auth["user_id"]
    return {"conversations": get_conversations_by_user(userid)}

@app.get("/history/{conversationid}")
def get_converastion_history(conversationid: int, auth=Depends(require_role(["admin", "user"]))):
    return {"history": get_history(conversationid)}

@app.post("/chat/{conversationid}")
def chat(conversationid: int,msg: Message, auth=Depends(require_role(["admin", "user"]))):
    conversations = get_conversations_by_user(auth["user_id"])
    if not any(conv["user_id"] == auth["user_id"] for conv in conversations):
        raise HTTPException(status_code=406, detail="Access denied: This user doesn't have permission to this conversation")

    if not any(conv["id"] == conversationid for conv in conversations):
        raise HTTPException(status_code=406, detail="Access denied")
    
    userinput = msg.usermessage
    response = generate_response(userinput, conversationid)
    historyid = add_history(conversationid, userinput, response)
    return {
        "historyid": historyid,
        "userinput": userinput,
        "response": response
    }

@app.post("/chat/rate/{historyid}")
def rate(historyid: int, hist: HistoryRate, auth=Depends(require_role(["admin", "user"]))):
    countrowsaffected = add_history_rate(historyid, hist.rate)
    return {
        "historyid": historyid,
        "countrowsaffected": countrowsaffected
    }
@app.post("/refresh")
def refresh(req: RefreshRequest):
    return new_access_token(req.refreshtoken)

@app.post("/logout")
def logout(req: RefreshRequest):
    rowaffected = revoke_refresh_token(req.refreshtoken)

    if rowaffected != 1:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return {"detail": "Logged out successfully"}
@app.get("/healthcheck")
def healthcheck():
    return {"status": "ready"}
"""
while True:
    user_input = input("Ty: ")
    if user_input.lower() == "exit":
        break
    response = generate_response(user_input)
    print("Asystent:", response)
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)