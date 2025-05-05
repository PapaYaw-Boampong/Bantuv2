from fastapi import FastAPI
from api.v1.api_router import router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Bantu API", version="1.0", description="API for User & Auth Testing")

# Allow frontend communication (adjust `origins` for your frontend)
origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# **Include only the Auth and User endpoints for now**
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Welcome to Bantu API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
