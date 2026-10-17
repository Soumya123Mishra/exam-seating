from django.shortcuts import render, redirect
from .db import students_col, rooms_col, seating_col, schools_col
from .ai_seating import generate_seating
from .ai_checker import detect_conflicts
from .pdf_generator import generate_pdf
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from bson.objectid import ObjectId
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.http import FileResponse
import os
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect

def register(request):

    if request.method == "POST":
        school_name = request.POST.get("school_name")
        username = request.POST.get("username")
        password = request.POST.get("password")

        # 🔥 Check if user exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists ❌")
            return redirect("register")

        # 🔥 Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            is_staff=True
        )

        # 🔥 Create school in MongoDB
        schools_col.insert_one({
            "name": school_name,
            "admin": username,
            "code": username.upper()  
        })

        messages.success(request, "Account created successfully ✅ Please login")
        return redirect("login")

    return render(request, "register.html")
def login_view(request):
    print("LOGIN VIEW HIT")

    if request.method == "POST":
        print("POST DATA:", request.POST)

        # ================= TEACHER LOGIN =================
        if request.POST.get("teacherForm") == "1":

            username = request.POST.get("username")
            password = request.POST.get("password")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid Teacher credentials")
        
        # ================= STUDENT LOGIN =================
        elif request.POST.get("studentForm") == "1": 

            roll = request.POST.get("username").strip()
            dob = request.POST.get("password").strip()


            # 🔥 IMPORTANT FIX
            student = students_col.find_one({
                "roll": {"$regex": f"^{roll}$", "$options": "i"},
                "dob": {"$regex": f"^{dob}$", "$options": "i"}
            })

            

            if student:
                request.session["student"] = roll
                return redirect("view_seating")
            else:
                messages.error(request, "Invalid Roll No or DOB") 
                return redirect("view_seating")
        else:
                messages.error(request, "Invalid Roll No or DOB")

    return render(request, "login.html")
from django.shortcuts import redirect

def redirect_after_login(request):
    if request.user.is_staff:
        return redirect('dashboard')
    else:
        return redirect('view_seating')

from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    # Agar teacher logged-in hain
    if request.user.is_authenticated:
        logout(request)

    # Agar student session active hai
    if "student" in request.session:
        del request.session["student"]

    messages.success(request, "Logged out successfully!")
    return redirect('login')
@staff_member_required
def dashboard(request):
    total_students = students_col.count_documents({})
    total_rooms = rooms_col.count_documents({})
    school = schools_col.find_one({"admin": request.user.username})
    school_id = school.get("code") if school else None
    students = list(students_col.find({"school_id": school_id}))
   #students = list(students_col.find())
    for s in students:
        s["id"]=str(s["_id"])
    rooms = list(rooms_col.find({"school_id": school_id}))
    for r in rooms:
        r["id"]=str(r["_id"])
    context = {
        'total_students': total_students,
        'total_rooms': total_rooms,
        'students': students,
        'rooms': rooms}
    return render(request, "dashboard.html",context)
@staff_member_required
def add_student(request):
    if request.method == "POST":
        roll = request.POST.get("roll", "").strip()
        name = request.POST.get("name", "").strip()
        course = request.POST.get("course", "").strip()
        subject = request.POST.get("subject", "").strip()
        year_sem = request.POST.get("year_sem", "").strip()
        dob = request.POST.get("dob", "").strip()
        
        # 1. Current logged-in admin ka school_id nikalein
        school = schools_col.find_one({"admin": request.user.username})
        school_id = school.get("code") if school else None

        if students_col.find_one({"roll": roll, "school_id": school_id}):
            messages.error(request, "Student with this Roll Number already exists in this school!")
            return redirect("add_student")

        # 2. Insert karte waqt school_id bhi pass karein
        students_col.insert_one({
            "roll": roll,
            "name": name,
            "course": course,
            "subject": subject,
            "year_sem": year_sem,
            "dob": dob,
            "school_id": school_id  # <--- Ye zaroori hai
        })

        if not User.objects.filter(username=roll).exists():
            user = User.objects.create_user(username=roll)
            user.set_password(dob)   
            user.save()

        messages.success(request, "Student added successfully!")
        return redirect("dashboard")
    
    return render(request, "add_student.html")

@staff_member_required
def update_student(request, student_id):
    student = students_col.find_one({"_id": ObjectId(student_id)})
    if not student:
        messages.error(request, "Student not found")
        return redirect("dashboard")
    student["id"] = str(student["_id"])
    if request.method == "POST":

        roll = request.POST.get("roll", "").strip()
        name = request.POST.get("name", "").strip()
        course = request.POST.get("course", "").strip()
        subject = request.POST.get("subject", "").strip()
        year_sem = request.POST.get("year_sem", "").strip()
        dob = request.POST.get("dob", "").strip()
        old_roll = student["roll"]
        students_col.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": {
                "roll": roll,
                "name": name,
                "course": course,
                "subject": subject,
                "year_sem": year_sem,
                "dob": dob
            }}
        )
        if User.objects.filter(username=old_roll).exists():
            user = User.objects.get(username=old_roll)

            user.username = roll     
            user.set_password(dob)   

            user.save()
        messages.success(request, "Student updated successfully")
        return redirect("dashboard")
    return render(request, "update_student.html", {"student": student})

@staff_member_required
def delete_student(request, student_id):
    student = students_col.find_one({"_id": ObjectId(student_id)})
    students_col.delete_one({"_id": ObjectId(student_id)})
    if User.objects.filter(username=student["roll"]).exists():
        User.objects.get(username=student["roll"]).delete()

    return redirect("dashboard")
import pandas as pd
from datetime import datetime
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def upload_students(request):

    if request.method == "POST":

        file = request.FILES.get("file")
        admin_username = request.user.username

        # 🔥 Auto detect school
        school = schools_col.find_one({"admin": admin_username})

        if not school:
            messages.error(request, "School not found")
            return redirect("dashboard")

        school_id = school.get("code")

        if not file:
            messages.error(request, "No file uploaded")
            return redirect("upload_students")

        try:
            # 📂 Read file
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            elif file.name.endswith(".xlsx"):
                df = pd.read_excel(file)
            else:
                messages.error(request, "Only CSV/Excel allowed")
                return redirect("upload_students")

            added = 0
            skipped = 0

            for _, row in df.iterrows():

                # 🔢 Roll number
                roll = str(row.get("roll")).split(".")[0].strip() 

                if not roll or roll == "nan":
                    skipped += 1
                    continue

                # 🔁 Duplicate check
                if students_col.find_one({
                    "roll": roll,
                    "school_id": school_id,
                    "course": str(row.get("course")).strip(),
                    "year_sem": str(row.get("year_sem")).strip()
                }):
                    skipped += 1
                    continue
                # 📅 DOB FORMAT FIX
                dob_raw = row.get("dob")

                try:
                    if pd.notna(dob_raw):
                        dob = pd.to_datetime(dob_raw).strftime("%d-%m-%Y")
                    else:
                        dob = ""
                except:
                    dob = str(dob_raw).strip()

                # 💾 Insert student
                students_col.insert_one({
                    "roll": roll,
                    "name": str(row.get("name")).strip(),
                    "course": str(row.get("course")).strip(),
                    "subject": str(row.get("subject")).strip(),
                    "year_sem": str(row.get("year_sem")).strip(),
                    "dob": dob,   # ✅ fixed format
                    "school_id": school_id
                })

                added += 1

            messages.success(
                request,
                f"{added} students added in {school_id}, {skipped} skipped"
            )

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

        return redirect("upload_students")

    return render(request, "upload_students.html")
from django.contrib import messages # सुनिश्चित करें कि यह इम्पोर्टेड हो

@staff_member_required
def add_room(request):
    if request.method == "POST":
        # एडमिन के हिसाब से स्कूल ढूंढें
        school = schools_col.find_one({"admin": request.user.username})
        
        # 🔥 अगर स्कूल नहीं मिला, तो ऑटोमैटिक एक स्कूल बना देंगे ताकि रूम सेव होना न रुके
        if not school:
            school_id = request.user.username.upper()
            schools_col.insert_one({
                "name": f"{request.user.username}'s School",
                "admin": request.user.username,
                "code": school_id
            })
        else:
            school_id = school.get("code")
            
        # फॉर्म का डेटा निकालें
        total_rows = int(request.POST.get("total_rows", 1))
        total_columns = int(request.POST.get("total_columns", 1))
        seats_per_bench = int(request.POST.get("seats_per_bench", 2))
        capacity = total_rows * total_columns * seats_per_bench

        # 🔥 मोंगोडीबी में रूम इंसर्ट करें
        rooms_col.insert_one({
            "room_no": request.POST.get("room_no"),
            "capacity": capacity,
            "seats_per_bench": seats_per_bench,
            "total_rows": total_rows,
            "total_columns": total_columns,
            "building_name": request.POST.get("building_name"),
            "floor_number": int(request.POST.get("floor_number", 0)),
            "room_type": request.POST.get("room_type"),
            "school_id": school_id   
        })
        
        messages.success(request, "Room added successfully! ✅")
        return redirect("dashboard") # रूम सेव होने के बाद सीधे डैशबोर्ड पर ले जाएगा जहाँ लिस्ट दिखेगी
        
    return render(request, "add_room.html")
@staff_member_required
def update_room(request, room_id):
    room = rooms_col.find_one({"_id": ObjectId(room_id)})
    room["id"]=str(room["_id"])
    if request.method == "POST":
        room_no = request.POST.get("room_no")
        total_rows = int(request.POST.get("total_rows"))
        total_columns = int(request.POST.get("total_columns"))
        seats_per_bench = int(request.POST.get("seats_per_bench", 2))
        capacity = total_rows * total_columns * seats_per_bench

        rooms_col.update_one(
            {"_id": ObjectId(room_id)},
            {"$set": {
                "room_no": room_no,
                "capacity": int(capacity),
               "seats_per_bench": int(request.POST.get("seats_per_bench", 2)),
               "total_rows": total_rows,
               "total_columns":total_columns,
                "building_name": request.POST.get("building_name"),
                "floor_number":int(request.POST["floor_number"]),
                "room_type": request.POST.get("room_type")
            }}
        )

        return redirect("dashboard")

    return render(request, "update_room.html", {"room": room})

@staff_member_required
def delete_room(request, room_id):
    rooms_col.delete_one({"_id": ObjectId(room_id)})
    return redirect("dashboard")

@staff_member_required
def download_pdf(request):

    seating = list(seating_col.find({}, {"_id": 0}))

    if not seating:
        return HttpResponse("No seating data found")
    generate_pdf(seating)

    return FileResponse(open("Seating_Arrangement.pdf", "rb"), as_attachment=True)
from .ai_seating import generate_seating
from .ai_checker import detect_conflicts
from .pdf_generator import generate_pdf
from .db import students_col, rooms_col, seating_col
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


# 🔥 AM/PM → 24hr convert function
def convert_to_24hr(time_str, ampm):
    hour, minute = map(int, time_str.split(":"))

    if ampm == "PM" and hour != 12:
        hour += 12
    elif ampm == "AM" and hour == 12:
        hour = 0

    return f"{hour:02}:{minute:02}"
@staff_member_required
def generate(request):

    if request.method != "POST":
        return render(request, "seating.html", {
            "seating": [],
            "alerts": ["Invalid request"]
        })

    #  FORM DATA 
    selected_date = request.POST.get("date")

    start_time = request.POST.get("start_time")
    start_ampm = request.POST.get("start_ampm")

    end_time = request.POST.get("end_time")
    end_ampm = request.POST.get("end_ampm")

    buildings = [b.strip() for b in request.POST.getlist("building[]")]
    floors = [int(f) for f in request.POST.getlist("floor[]")]
    room_types = [r.strip() for r in request.POST.getlist("room_type[]")]

    alerts = []

    #  VALIDATION 
    if not selected_date or not start_time or not end_time:
        alerts.append("Please select exam date and full timing")

    if not buildings:
        alerts.append("Please select building")

    if not floors:
        alerts.append("Please select floor")

    if not room_types:
        alerts.append("Please select room type")

    if alerts:
        return render(request, "seating.html", {
            "seating": [],
            "alerts": alerts
        })

    # TIME CONVERSION 
    start_time_24 = convert_to_24hr(start_time, start_ampm)
    end_time_24 = convert_to_24hr(end_time, end_ampm)

    display_time = f"{start_time} {start_ampm} - {end_time} {end_ampm}"

    #  GET SCHOOL
    school = schools_col.find_one({"admin": request.user.username})

    if not school:
        messages.error(request, "⚠️ School not found")
        return redirect("school_settings")

    school_id = school.get("code")

    #  FETCH STUDENTS 
    students = list(students_col.find({
    "school_id": school_id   # 🔥 ADD THIS
}, {"_id": 0}))
    if not students:
        return render(request, "seating.html", {
            "seating": [],
            "alerts": ["No students found"]
        })

    #  FETCH ROOMS 
    rooms = list(rooms_col.find({
        "school_id": school_id, 
        "building_name": {"$in": buildings},
        "floor_number": {"$in": floors},
        "room_type": {"$in": room_types}
    }, {"_id": 0}))

    if not rooms:
        return render(request, "seating.html", {
            "seating": [],
            "alerts": ["No rooms found for selected filters"]
        })

    #  REMOVE DUPLICATES 
    unique_rooms = []
    seen = set()

    for room in rooms:
        key = (
            room.get("building_name"),
            room.get("floor_number"),
            room.get("room_no"),
            room.get("room_type")
        )

        if key not in seen:
            seen.add(key)
            unique_rooms.append(room)

    rooms = unique_rooms

    #  SORT ROOMS 
    rooms = sorted(
        rooms,
        key=lambda r: (
            r.get("building_name", ""),
            r.get("floor_number", ""),
            r.get("room_no", ""),
            r.get("room_type", "")
        )
    )

    #  GENERATE SEATING
    seating, gen_alerts = generate_seating(
        students,
        rooms,
        selected_date,
        start_time_24,
        end_time_24
    )

    alerts.extend(gen_alerts)

   
    for s in seating:
        s["display_time"] = display_time
        s["school_id"] = school_id   

    #  DELETE OLD 
    seating_col.delete_many({

        "school_id": school_id 
    })

    # INSERT NEW 
    if seating:
        seating_col.insert_many(seating)

   
    try:
        conflict_alerts = detect_conflicts(seating)
        alerts.extend(conflict_alerts)
    except Exception as e:
        alerts.append(f"Conflict check failed: {str(e)}")

    #  PDF 
    try:
        generate_pdf(seating)
    except Exception as e:
        alerts.append(f"PDF generation failed: {str(e)}")

    for alert in alerts:
           messages.warning(request, alert)

    return redirect("view_seating")
def view_seating(request):

    query = request.GET.get("q")
    exam_date = request.GET.get("date")

    is_teacher = request.user.is_authenticated and request.user.is_staff
    is_student = "student" in request.session

    if not is_teacher and not is_student:
        return redirect("login")

    #  ADMIN 
    if is_teacher:

        school = schools_col.find_one({"admin": request.user.username})
        school_id = school.get("code") if school else None

        filter_query = {
            "school_id": school_id
        }

        if query and query.strip():
            filter_query["$or"] = [
                {"roll": {"$regex": f"^{query.strip()}$", "$options": "i"}},
                {"name": {"$regex": query.strip(), "$options": "i"}}
            ]

        if exam_date:
            filter_query["exam_date"] = exam_date
        seating = list(
            seating_col.find(filter_query, {"_id": 0}).sort([
                ("course", 1),
                ("year_sem", 1),
                ("exam_date", 1),
                ("start_time", 1),
                ("room_no", 1),
                ("row", 1),
                ("column", 1)
            ])
        )

        if not seating:
            return render(request, "seating.html", {
                "seating": [],
                "is_admin": True
            })

        # ✅ Normalize
        for s in seating:
            s["course"] = s.get("course", "").strip().upper()
            s["year_sem"] = s.get("year_sem", "").strip().upper()
            s["group"] = f"{s['course']} - {s['year_sem']}"

        return render(request, "seating.html", {
            "seating": seating,
            "is_admin": True
        })

    #  STUDENT 
    else:

        roll = request.session.get("student")

        if not roll:
            return redirect("login")

        seat = seating_col.find_one(
            {"roll": str(roll).strip()},
            {"_id": 0},
            sort=[("_id", -1)]
        )

        if seat and "display_time" not in seat:
            start = seat.get("start_time", "")
            end = seat.get("end_time", "")
            seat["display_time"] = f"{start} - {end}"

        school = {}
        if seat and "school_id" in seat:
            school = schools_col.find_one({"code": seat["school_id"]}) or {}

        return render(request, "seating.html", {
            "seat": seat,
            "is_admin": False,
            "school_logo": school.get("logo"),
            "school_name": school.get("name")
        })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
import os
import time

@login_required
def school_settings(request):

    if not request.user.is_staff:
        return redirect("dashboard")
    school = schools_col.find_one({"admin": request.user.username}) or {}

    if request.method == "POST":

        name = request.POST.get("school_name")
        logo = request.FILES.get("logo")

        update_data = {"name": name}
        if logo:
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            filename = str(int(time.time())) + "_" + logo.name
            file_path = os.path.join(settings.MEDIA_ROOT, filename)

            # Save file
            with open(file_path, 'wb+') as f:
                for chunk in logo.chunks():
                    f.write(chunk)
            old_logo = school.get("logo")
            if old_logo:
                old_path = os.path.join(settings.MEDIA_ROOT, old_logo)
                if os.path.exists(old_path):
                    os.remove(old_path)

            update_data["logo"] = filename

        # 🔥 Save to DB
        schools_col.update_one(
    {"admin": request.user.username},
    {"$set": update_data},
    upsert=True
)

        messages.success(request, "✅ School settings updated successfully!")

        return redirect("school_settings")

    return render(request, "school_settings.html", {"school": school})