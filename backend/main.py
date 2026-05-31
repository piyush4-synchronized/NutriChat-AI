from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Nutrition AI backend is running."}
