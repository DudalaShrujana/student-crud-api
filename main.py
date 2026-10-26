
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, EmailStr


# --------------------------------------------------
# 1. Create the FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="Student CRUD API",
    description="A REST API for managing student records using FastAPI and SQLite",
    version="1.0.0",
)


# --------------------------------------------------
# 2. Configure the SQLite database
# --------------------------------------------------

DATABASE_PATH = Path(__file__).resolve().parent / "students.db"


@contextmanager
def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# --------------------------------------------------
# 3. Create the students table automatically
# --------------------------------------------------

def create_student_table():
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                course TEXT NOT NULL
            )
            """
        )


@app.on_event("startup")
def startup():
    create_student_table()


# --------------------------------------------------
# 4. Define the student input model
# --------------------------------------------------

class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    course: str = Field(min_length=2, max_length=100)


# --------------------------------------------------
# 5. Home endpoint
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Student CRUD API is running!",
        "status": "success",
    }


# --------------------------------------------------
# 6. Check the database connection and table
# --------------------------------------------------

@app.get("/db-check")
def database_check():
    with get_db_connection() as connection:
        result = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'students'
            """
        ).fetchone()

    return {
        "database": "connected",
        "student_table_exists": result is not None,
    }


# --------------------------------------------------
# 7. CREATE: Add a new student
# --------------------------------------------------

@app.post("/students", status_code=201)
def create_student(student: StudentCreate):
    try:
        with get_db_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO students (name, email, course)
                VALUES (?, ?, ?)
                """,
                (student.name, student.email, student.course),
            )

            student_id = cursor.lastrowid

            result = connection.execute(
                """
                SELECT id, name, email, course
                FROM students
                WHERE id = ?
                """,
                (student_id,),
            ).fetchone()

            return dict(result)

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="A student with this email already exists.",
        )



# --------------------------------------------------
# 8. READ: Get all students
# --------------------------------------------------

@app.get("/students")
def get_all_students():
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, email, course
            FROM students
            ORDER BY id
            """
        ).fetchall()

    return [dict(row) for row in rows]


# --------------------------------------------------
# 9. READ: Get one student by ID
# --------------------------------------------------

@app.get("/students/{student_id}")
def get_student(student_id: int):
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, email, course
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return dict(row)



# --------------------------------------------------
# 10. UPDATE: Replace a student's details
# --------------------------------------------------

@app.put("/students/{student_id}")
def update_student(student_id: int, student: StudentCreate):
    try:
        with get_db_connection() as connection:
            existing_student = connection.execute(
                "SELECT id FROM students WHERE id = ?",
                (student_id,),
            ).fetchone()

            if existing_student is None:
                raise HTTPException(
                    status_code=404,
                    detail="Student not found",
                )

            connection.execute(
                """
                UPDATE students
                SET name = ?, email = ?, course = ?
                WHERE id = ?
                """,
                (
                    student.name,
                    student.email,
                    student.course,
                    student_id,
                ),
            )

            updated_student = connection.execute(
                """
                SELECT id, name, email, course
                FROM students
                WHERE id = ?
                """,
                (student_id,),
            ).fetchone()

            return dict(updated_student)

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="A student with this email already exists.",
        )



# --------------------------------------------------
# 11. DELETE: Remove a student by ID
# --------------------------------------------------

@app.delete("/students/{student_id}")
def delete_student(student_id: int):
    with get_db_connection() as connection:
        existing_student = connection.execute(
            "SELECT id FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()

        if existing_student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found",
            )

        connection.execute(
            "DELETE FROM students WHERE id = ?",
            (student_id,),
        )

    return {
        "message": "Student deleted successfully",
        "student_id": student_id,
    }
