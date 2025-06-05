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

app = FastAPI()

# ────────────────────────────────────────
# Paths & template / static setup
# ────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
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

# ────────────────────────────────────────
# In-memory data (sample dataset)
# ────────────────────────────────────────
courses = [
    {"id": 1, "name": "B.Tech Computer Science", "stream": "Science", "duration": "4 years", "colleges": ["IIT Delhi", "NIT Trichy"], "seats": 500, "avg_fee": 150000},
    {"id": 2, "name": "B.Com", "stream": "Commerce", "duration": "3 years", "colleges": ["SRCC", "Loyola"], "seats": 300, "avg_fee": 60000},
    {"id": 3, "name": "BA English", "stream": "Arts", "duration": "3 years", "colleges": ["Delhi University", "JNU"], "seats": 400, "avg_fee": 50000},
    {"id": 4, "name": "MBBS", "stream": "Science", "duration": "5.5 years", "colleges": ["AIIMS", "CMC Vellore"], "seats": 200, "avg_fee": 300000},
    {"id": 5, "name": "BBA", "stream": "Commerce", "duration": "3 years", "colleges": ["NMIMS", "IIM Bangalore"], "seats": 350, "avg_fee": 120000},
]

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

# ────────────────────────────────────────
# Database dependency
# ────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ────────────────────────────────────────
# Home route ➜ show colleges
# ────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    college_filter: Optional[str] = None,
    course_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=302)
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Start with all colleges
    filtered_colleges = colleges

    # Apply text query filter if present
    if q:
        q_lower = q.lower()
        filtered_colleges = [
            c for c in filtered_colleges if q_lower in c["name"].lower() or q_lower in c["location"].lower()
        ]

    # Filter by college name if filter selected
    if college_filter:
        filtered_colleges = [c for c in filtered_colleges if c["name"] == college_filter]

    # Filter by location if filter selected
    if location_filter:
        filtered_colleges = [c for c in filtered_colleges if c["location"] == location_filter]

    # Filter by course if selected (college should offer that course)
    if course_filter:
        filtered_colleges = [c for c in filtered_colleges if course_filter in c["courses"]]

    # Prepare lists for dropdown options - unique and sorted
    college_names = sorted(set(c["name"] for c in colleges))
    all_courses = sorted(set(c["name"] for c in courses))  # <-- FIXED THIS LINE
    locations = sorted(set(c["location"] for c in colleges))

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "colleges": filtered_colleges,
            "query": q or "",
            "college_names": college_names,
            "courses": all_courses,
            "locations": locations,
            "selected_college": college_filter,
            "selected_course": course_filter,
            "selected_location": location_filter,
        },
    )

# ────────────────────────────────────────
# Auth routes
# ────────────────────────────────────────
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
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": user.username})

@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("user_id")
    return response

# ────────────────────────────────────────
# Course routes
# ────────────────────────────────────────
@app.get("/courses", response_class=HTMLResponse)
def list_courses(request: Request, stream: Optional[str] = None):
    filtered = [c for c in courses if c["stream"].lower() == stream.lower()] if stream else courses
    for course in filtered:
        fee = course.get("avg_fee")
        course["formatted_fee"] = "{:,}".format(fee) if isinstance(fee, (int, float)) else "N/A"
    return templates.TemplateResponse("courses.html", {"request": request, "courses": filtered})

@app.get("/courses/{course_slug}", response_class=HTMLResponse)
def course_detail(request: Request, course_slug: str):
    course = next((c for c in courses if c["name"].lower().replace(" ", "-") == course_slug), None)
    if not course:
        return JSONResponse(status_code=404, content={"message": "Course not found"})
    return templates.TemplateResponse("course_detail.html", {"request": request, "course": course})

# ────────────────────────────────────────
# College routes
# ────────────────────────────────────────
@app.get("/colleges", response_class=HTMLResponse)
def list_colleges(request: Request):
    return templates.TemplateResponse("colleges.html", {"request": request, "colleges": colleges})

@app.get("/colleges-live", response_class=HTMLResponse)
async def colleges_live(request: Request, limit: int = 10):
    url = (
        "https://api.data.gov.in/resource/cd09cb48-4e44-489f-96b5-fc7012bf5f8e"
        "?api-key=579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
        "&format=json&limit=" + str(limit)
    )
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()
    items = data.get("records", [])
    mapped = [
        {
            "name": c.get("college_name", "N/A"),
            "location": f"{c.get('district_name', '')}, {c.get('state_name', '')}",
            "university": c.get("university_name", "N/A"),
            "status": c.get("status", "N/A"),
        }
        for c in items
    ]
    return templates.TemplateResponse("colleges.html", {"request": request, "colleges": mapped, "live_api": True})

# ────────────────────────────────────────
# Compare / Suggest API
# ────────────────────────────────────────
@app.get("/compare", response_class=HTMLResponse)
def compare(request: Request, course_ids: Optional[List[int]] = Query([]), college_ids: Optional[List[int]] = Query([])):
    selected_courses = [c for c in courses if c["id"] in course_ids]
    selected_colleges = [c for c in colleges if c["id"] in college_ids]
    return templates.TemplateResponse("compare.html", {"request": request, "courses": selected_courses, "colleges": selected_colleges})

@app.get("/api/suggestions")
def suggestions(q: str):
    q_lower = q.lower()
    return JSONResponse({
        "courses": [c["name"] for c in courses if q_lower in c["name"].lower()][:5],
        "colleges": [c["name"] for c in colleges if q_lower in c["name"].lower()][:5],
    })

# ────────────────────────────────────────
# Run locally
# ────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
