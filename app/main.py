from fastapi import FastAPI

from app.routers import vehicle

app = FastAPI(title="Vehicle Info API")

app.include_router(vehicle.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
