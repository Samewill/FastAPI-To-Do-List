from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, update
from pydantic import BaseModel
from datetime import date

# Request model (for POST)
class TaskCreate(BaseModel):
    title: str
    completed: Optional[bool] = False
    created_at: Optional[date] = None  

#  Request model(for PUT)
class UpdateTask(BaseModel):
    title : str
    completed: bool 

#Creating a model
class Task(SQLModel, table=True):
    id : Optional[int] = Field( default = None, primary_key = True)
    title : str = Field(index = True)
    completed : bool = Field(default = False)
    created_at : date = Field(default_factory = date.today)


# Creating an engine
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

# Create the Tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Create task
@app.post("/tasks/")
def create_task(task: TaskCreate, session: SessionDep) -> Task:
    db_task = Task.from_orm(task)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

# get many tasks filtered by completion status and order by date
@app.get("/tasks")
def get_tasks(session : SessionDep, 
              offset : int = 0, 
              limit: Annotated[int, Query(le=20)] = 20,
              status : Optional[bool] = None
              ) -> list[Task]:
    query = select(Task)

    if status is True:
        query = query.where(Task.completed == True)
    if status is False:
        query = query.where(Task.completed == False)

    tasks = session.exec(query.order_by(Task.created_at).offset(offset).limit(limit)).all()
    return tasks

# get single task by id
@app.get("/tasks/{task_id}")
def get_task(task_id: int, session: SessionDep) -> Task:

    task = session.exec(select(Task).where(Task.id == task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

@app.put("/tasks/{task_id}")
def update_task(task_id : int, updated_task : UpdateTask, session : SessionDep) -> Task:
    task = session.get(Task, task_id)

    if not task:
        raise HTTPException(status_code = 404, detail = "Not Found: Requested task doesn't exist ")
    
    # Update fields
    task.title = updated_task.title
    task.completed = updated_task.completed

    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@app.patch("/tasks/{task_id}")
def partial_update(task_id : int, session : SessionDep, updated_task : Optional[UpdateTask] = None) -> Task:
    task = session.get(Task, task_id)

    if not task :
        raise HTTPException(status_code = 404, detail= "Not Found: Requested task doesn't exist")
    
    # Update only provided fields
    if updated_task.title is not None:
        task.title = updated_task.title
    if updated_task.completed is not None:
        task.completed = updated_task.completed

    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@app.delete("/tasks/{task_id}")
def delete_task(task_id : int, session : SessionDep):
    task = session.exec(select(Task).where(Task.id == task_id)).first()

    if not task :
        raise HTTPException(status_code = 404, detail= "Not Found: Requested task doesn't exist")
    
    session.delete(task)
    session.commit()
    return {"task deleted", True}
