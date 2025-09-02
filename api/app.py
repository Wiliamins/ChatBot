from fastapi import FastAPI
app = FastAPI(root_path="/api")

@app.get("/health")  # без префикса /api!
def health():
    return {"ok": True}

@app.get("/")        # чтобы /api/ тоже отвечал
def root():
    return {"status": "alive"}
