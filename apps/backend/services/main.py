from fastapi import FastAPI

app = FastAPI(title="PropPal API")


@app.get("/")
def health_check():
    return {"status": "ok changed"}


@app.get("/chat")
def chat():
    return {"answer": f"You said: kkkl"}
