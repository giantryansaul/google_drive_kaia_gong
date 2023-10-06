# Description: Mock Gong server for testing purposes

from typing import List
import random

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

app = FastAPI()

@app.post("/reset")
def read_root():
    """
    Put a breakpoint here to reset the mock server
    """
    print(f"--------- Reset Point ---------\n")
    return {"info": "Reset Point"}

class Party(BaseModel):
    name: str
    userId: str | None = None

class Call(BaseModel):
    clientUniqueId: str
    title: str
    actualStart: str
    parties: List[Party]
    primaryUser: str
    direction: str

@app.post("/v2/calls")
def post_call(call: Call):
    parties = ",".join([f"{party.name}[{party.userId}]" for party in call.parties])
    print(f"Received call\nclientUniqueId: {call.clientUniqueId}\ntitle: {call.title}\nactualStart: {call.actualStart}\nparties: {parties}\nprimaryUser: {call.primaryUser}\ndirection: {call.direction}")
    return {"callId": random.randint(1000, 9999)}

@app.put("/v2/calls/{call_id}/media")
def post_call_media(call_id: str, mediaFile: UploadFile = File(...)):
    print(f"Received file: {mediaFile.filename} for call: {call_id}")
    return {"url": f'https://gong.io?callId={call_id}'}