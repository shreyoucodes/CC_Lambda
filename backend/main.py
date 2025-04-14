from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from database import Base, engine, SessionLocal, FunctionModel
from execution_engine.docker_executor import generate_code, execute_in_docker

app = FastAPI()

Base.metadata.create_all(bind=engine)

# Pydantic model (request/response)
class Function(BaseModel):
    name: str
    route: str
    language: str
    timeout: int

    class Config:
        orm_mode = True

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Serverless Function API is live"}


from fastapi import Depends
from sqlalchemy.orm import Session
from database import FunctionModel

# CREATE
@app.post("/functions/", response_model=Function)
def create_function(function: Function, db: Session = Depends(get_db)):
    db_func = FunctionModel(**function.dict())
    db.add(db_func)
    db.commit()
    db.refresh(db_func)
    return db_func

# READ ALL
@app.get("/functions/", response_model=List[Function])
def list_functions(db: Session = Depends(get_db)):
    return db.query(FunctionModel).all()

# READ BY ID
@app.get("/functions/{func_id}", response_model=Function)
def get_function(func_id: int, db: Session = Depends(get_db)):
    func = db.query(FunctionModel).filter(FunctionModel.id == func_id).first()
    if func is None:
        raise HTTPException(status_code=404, detail="Function not found")
    return func

# DELETE
@app.delete("/functions/{func_id}")
def delete_function(func_id: int, db: Session = Depends(get_db)):
    func = db.query(FunctionModel).filter(FunctionModel.id == func_id).first()
    if not func:
        raise HTTPException(status_code=404, detail="Function not found")
    db.delete(func)
    db.commit()
    return {"message": "Function deleted"}

from fastapi import Body

@app.post("/functions/execute")
def execute_function(
    language: str = Body(...),
    code: str = Body(...),
    timeout: int = Body(5)
):
    try:
        print("👉 Language:", language)
        print("👉 Code:", code)
        print("👉 Timeout:", timeout)

        uid, file_path, image, filename = generate_code(language, code)
        output, error = execute_in_docker(uid, image, filename, timeout)
        
        print("✅ Output:", output)
        print("⚠️ Error:", error)

        return {
            "output": output,
            "error": error
        }
    except Exception as e:
        print("🔥 EXCEPTION:", e)
        raise HTTPException(status_code=500, detail=str(e))

