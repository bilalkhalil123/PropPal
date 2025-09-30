from fastapi import FastAPI

app = FastAPI(title="PropPal API")


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/chat")
def chat(query: dict):
    return {"answer": f"You said: {query.get('query')}"}
