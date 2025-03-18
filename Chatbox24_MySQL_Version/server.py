from fastapi import FastAPI, HTTPException
import ollama

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "RAG Email Automation API is running!"}

@app.post("/generate")
def generate_response(user_input: str):
    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": user_input}]
        )
        return {"response": response["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
