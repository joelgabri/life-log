from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db
from .routers import entries, keys, owntracks, waistline

app = FastAPI(title="Life Log")

app.include_router(entries.router, prefix="/api/v1")
app.include_router(keys.router, prefix="/api/v1")
app.include_router(owntracks.router, prefix="/api/v1")
app.include_router(waistline.router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error"})
    return {"status": "ok"}
