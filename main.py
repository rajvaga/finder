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
    {"id": 1, "name": "B.Tech Computer Science", "stream": "Science", "duration": "4 years", 
     "colleges": ["IIT Delhi", "NIT Trichy", "NMIMS"], "seats": 600, "avg_fee": 150000},
     
    {"id": 2, "name": "B.Tech Electrical", "stream": "Science", "duration": "4 years", 
     "colleges": ["IIT Delhi"], "seats": 150, "avg_fee": 140000},
     
    {"id": 3, "name": "B.Tech Mechanical", "stream": "Science", "duration": "4 years", 
     "colleges": ["NIT Trichy"], "seats": 150, "avg_fee": 135000},
     
    {"id": 4, "name": "B.Com", "stream": "Commerce", "duration": "3 years", 
     "colleges": ["SRCC", "Loyola", "Delhi University", "NMIMS"], "seats": 800, "avg_fee": 65000},
     
    {"id": 5, "name": "BA English", "stream": "Arts", "duration": "3 years", 
     "colleges": ["Delhi University", "JNU", "Loyola", "NIT Trichy"], "seats": 700, "avg_fee": 55000},
     
    {"id": 6, "name": "BA Political Science", "stream": "Arts", "duration": "3 years", 
     "colleges": ["JNU"], "seats": 100, "avg_fee": 50000},
     
    {"id": 7, "name": "BA Economics", "stream": "Arts", "duration": "3 years", 
     "colleges": ["SRCC", "IIM Bangalore"], "seats": 200, "avg_fee": 60000},
     
    {"id": 8, "name": "B.Sc Maths", "stream": "Science", "duration": "3 years", 
     "colleges": ["Delhi University"], "seats": 120, "avg_fee": 40000},
     
    {"id": 9, "name": "MBBS", "stream": "Science", "duration": "5.5 years", 
     "colleges": ["AIIMS", "CMC Vellore"], "seats": 250, "avg_fee": 300000},
     
    {"id": 10, "name": "B.Sc Nursing", "stream": "Science", "duration": "4 years", 
     "colleges": ["AIIMS", "CMC Vellore"], "seats": 180, "avg_fee": 100000},
     
    {"id": 11, "name": "MD General Medicine", "stream": "Science", "duration": "3 years", 
     "colleges": ["AIIMS"], "seats": 50, "avg_fee": 350000},
     
    {"id": 12, "name": "BPT", "stream": "Science", "duration": "4.5 years", 
     "colleges": ["CMC Vellore"], "seats": 60, "avg_fee": 110000},
     
    {"id": 13, "name": "BBA", "stream": "Commerce", "duration": "3 years", 
     "colleges": ["NMIMS", "IIM Bangalore", "SRCC", "Loyola", "Delhi University"], "seats": 900, "avg_fee": 125000},
     
    {"id": 14, "name": "MBA", "stream": "Commerce", "duration": "2 years", 
     "colleges": ["IIM Bangalore"], "seats": 200, "avg_fee": 250000},
     
    {"id": 15, "name": "MA Economics", "stream": "Arts", "duration": "2 years", 
     "colleges": ["JNU"], "seats": 100, "avg_fee": 60000},
]

colleges = [
    {"id": 1, "name": "IIT Delhi", "courses": ["B.Tech Computer Science", "B.Tech Electrical", "BBA"], "location": "Delhi"},
    {"id": 2, "name": "NIT Trichy", "courses": ["B.Tech Computer Science", "B.Tech Mechanical", "BA English"], "location": "Tamil Nadu"},
    {"id": 3, "name": "SRCC", "courses": ["B.Com", "BBA", "BA Economics"], "location": "Delhi"},
    {"id": 4, "name": "Loyola", "courses": ["B.Com", "BA English", "BBA"], "location": "Chennai"},
    {"id": 5, "name": "Delhi University", "courses": ["BA English", "B.Com", "B.Sc Maths", "BBA"], "location": "Delhi"},
    {"id": 6, "name": "JNU", "courses": ["BA English", "BA Political Science", "MA Economics"], "location": "Delhi"},
    {"id": 7, "name": "AIIMS", "courses": ["MBBS", "B.Sc Nursing", "MD General Medicine"], "location": "Delhi"},
    {"id": 8, "name": "CMC Vellore", "courses": ["MBBS", "B.Sc Nursing", "BPT"], "location": "Tamil Nadu"},
    {"id": 9, "name": "NMIMS", "courses": ["BBA", "B.Com", "B.Tech Computer Science"], "location": "Mumbai"},
    {"id": 10, "name": "IIM Bangalore", "courses": ["BBA", "BA Economics", "MBA"], "location": "Bangalore"},
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
    course_names = sorted(set(c["name"] for c in courses))
    return templates.TemplateResponse("signup.html", {"request": request, "courses": course_names})


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
def list_courses(
    request: Request,
    stream: Optional[str] = Query(None),
    course_name: Optional[str] = Query(None),
    college_name: Optional[str] = Query(None)
):
    filtered = courses

    # Filter by stream if provided
    if stream:
        filtered = [c for c in filtered if c["stream"].lower() == stream.lower()]

    # Filter by course name if provided
    if course_name:
        filtered = [c for c in filtered if c["name"].lower() == course_name.lower()]

    # Filter by college name if provided
    if college_name:
        filtered = [c for c in filtered if college_name.lower() in [col.lower() for col in c.get("colleges", [])]]

    # Format fee for display
    for course in filtered:
        fee = course.get("avg_fee")
        course["formatted_fee"] = "{:,}".format(fee) if isinstance(fee, (int, float)) else "N/A"

    # Extract unique streams, course names, colleges for dropdowns
    streams = sorted(set(c["stream"] for c in courses))
    course_names = sorted(set(c["name"] for c in courses))
    colleges = sorted(set(col for c in courses for col in c.get("colleges", [])))

    return templates.TemplateResponse("courses.html", {
        "request": request,
        "courses": filtered,
        "streams": streams,
        "course_names": course_names,
        "colleges": colleges,
        "selected_stream": stream,
        "selected_course_name": course_name,
        "selected_college_name": college_name
    })
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

@app.get("/college/{college_id}", response_class=HTMLResponse)
def college_detail(request: Request, college_id: int):
    # Find college by id
    college = next((c for c in colleges if c["id"] == college_id), None)
    if not college:
        return JSONResponse(status_code=404, content={"message": "College not found"})

    # Find courses details offered by this college (optional: enrich with course info)
    offered_courses = [c for c in courses if c["name"] in college["courses"]]

    return templates.TemplateResponse(
        "college_detail.html",
        {
            "request": request,
            "college": college,
            "courses": offered_courses,
        }
    )


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
