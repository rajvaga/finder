import pdfplumber
import re
import json

def extract_courses(pdf_path):
    courses = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')
            for line in lines:
                match = re.match(r'^\s*(\d+)\s+([A-Za-z &]+)\s+(.+?)\s+([A-Za-z .]+)\s+([A-Za-z .]+)\s+(UG|PG)\s+(\d+)', line)
                if match:
                    course = {
                        's_no': match.group(1),
                        'subject': match.group(2).strip(),
                        'title': match.group(3).strip(),
                        'coordinator': match.group(4).strip(),
                        'university': match.group(5).strip(),
                        'level': match.group(6).strip(),
                        'credits': match.group(7).strip()
                    }
                    courses.append(course)
    return courses

# Run the script
pdf_path = r'E:\college_finder_app\Course_List_approved_by_SWAYAM_Board_2024_January_Semester.pdf'


courses = extract_courses(pdf_path)

# Save to JSON
with open(r'E:\college_finder_app\data\courses.json', 'w', encoding='utf-8') as f:

    json.dump(courses, f, ensure_ascii=False, indent=4)

print(f"Extracted {len(courses)} courses and saved to courses.json")
