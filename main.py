from fastapi import FastAPI, Form, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from passlib.hash import bcrypt
from typing import Optional, List
import os
import httpx
import json

app = FastAPI()

# Directories
BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data", "courses.json")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load courses from JSON file
def load_courses():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

courses = load_courses()

# Example hardcoded colleges (you can move this to a JSON as well)
colleges = [
    {"id": 1, "name": "IIT Delhi", "courses": ["B.Tech Computer Science"], "location": "Delhi"},
    {"id": 2, "name": "NIT Trichy", "courses": ["B.Tech Computer Science"], "location": "Tamil Nadu"},
    {"id": 3, "name": "SRCC", "courses": ["B.Com"], "location": "Delhi"},
    {"id": 4, "name": "Loyola", "courses": ["B.Com"], "location": "Chennai"},
    {"id": 5, "name": "Delhi University", "courses": ["BA English"], "location": "Delhi"},
    {"id": 6, "name": "JNU", "courses": ["BA English"], "location": "Delhi"},
    {"id": 7, "name": "AIIMS", "courses": ["MBBS"], "location": "Delhi"},
    {"id": 8, "name": "CMC Vellore", "courses": ["MBBS"], "location": "Tamil Nadu"},
    {"id": 9, "name": "NMIMS", "courses": ["BBA"], "location": "Mumbai"},
    {"id": 10, "name": "IIM Bangalore", "courses": ["BBA"], "location": "Bangalore"},
]

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db), q: Optional[str] = None, stream: Optional[str] = None):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return templates.TemplateResponse("login.html", {"request": request})
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})

    filtered = courses
    if stream:
        filtered = [
            c for c in filtered
            if c.get("stream") and c["stream"].lower() == stream.lower()
        ]
    if q:
        q = q.lower()
        filtered = [
            c for c in filtered
            if q in c.get("name", "").lower()
        ]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "courses": filtered,
        "query": q or "",
        "stream": stream or ""
    })
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not bcrypt.verify(password, user.password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie("user_id", str(user.id), httponly=True)
    return response

@app.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
def signup(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered"})
    new_user = User(username=username, email=email, password=bcrypt.hash(password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie("user_id", str(new_user.id), httponly=True)
    return response

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": user.username })

@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("user_id")
    return response

@app.get("/courses", response_class=HTMLResponse)
def list_courses(request: Request, stream: Optional[str] = None):
    filtered = [c for c in courses if c["stream"].lower() == stream.lower()] if stream else courses

    # Format avg_fee to readable string
    for course in filtered:
        if "avg_fee" in course and isinstance(course["avg_fee"], (int, float)):
            course["formatted_fee"] = "{:,}".format(course["avg_fee"])
        else:
            course["formatted_fee"] = "N/A"

    return templates.TemplateResponse("courses.html", {"request": request, "courses": filtered})

@app.get("/courses/{course_slug}", response_class=HTMLResponse)
def course_detail(request: Request, course_slug: str):
    course = next((c for c in courses if c["name"].lower().replace(" ", "-") == course_slug), None)
    if not course:
        return JSONResponse(status_code=404, content={"message": "Course not found"})
    return templates.TemplateResponse("course_detail.html", {"request": request, "course": course})

@app.get("/colleges", response_class=HTMLResponse)
def list_colleges(request: Request):
    return templates.TemplateResponse("colleges.html", {"request": request, "colleges": colleges})

@app.get("/compare", response_class=HTMLResponse)
def compare(request: Request, course_ids: Optional[List[int]] = Query([]), college_ids: Optional[List[int]] = Query([])):
    selected_courses = [c for c in courses if c["id"] in course_ids]
    selected_colleges = [c for c in colleges if c["id"] in college_ids]
    return templates.TemplateResponse("compare.html", {"request": request, "courses": selected_courses, "colleges": selected_colleges})

@app.get("/api/suggestions")
def suggestions(q: str):
    q = q.lower()
    return JSONResponse({
        "courses": [c["name"] for c in courses if q in c["name"].lower()][:5],
        "colleges": [c["name"] for c in colleges if q in c["name"].lower()][:5]
    })

@app.get("/colleges-live", response_class=HTMLResponse)
async def colleges_live(request: Request, limit: int = 10):
    url = "https://api.data.gov.in/resource/cd09cb48-4e44-489f-96b5-fc7012bf5f8e?api-key=579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b&format=json&limit=" + str(limit)
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()
    items = data.get("records", [])
    mapped = [{
        "name": c.get("college_name", "N/A"),
        "location": f"{c.get('district_name', '')}, {c.get('state_name', '')}",
        "university": c.get("university_name", "N/A"),
        "status": c.get("status", "N/A")
    } for c in items]
    return templates.TemplateResponse("colleges.html", {"request": request, "colleges": mapped, "live_api": True})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
