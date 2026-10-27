from django.shortcuts import render, redirect, get_object_or_404
from .models import School, Student, Room, Seating
from .ai_seating import generate_seating
from .ai_checker import detect_conflicts
from .pdf_generator import generate_pdf
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.conf import settings
import os
import time
import pandas as pd
from datetime import datetime

def register(request):
    if request.method == "POST":
        school_name = request.POST.get("school_name")
        username = request.POST.get("username")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists ❌")
            return redirect("register")

        user = User.objects.create_user(
            username=username,
            password=password,
            is_staff=True
        )

        School.objects.create(
            name=school_name,
            admin=username,
            code=username.upper()
        )

        messages.success(request, "Account created successfully ✅ Please login")
        return redirect("login")

    return render(request, "register.html")

def login_view(request):
    print("LOGIN VIEW HIT")

    if request.method == "POST":
        print("POST DATA:", request.POST)

        if request.POST.get("teacherForm") == "1":
            username = request.POST.get("username")
            password = request.POST.get("password")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid Teacher credentials")
        
        elif request.POST.get("studentForm") == "1": 
            roll = request.POST.get("username").strip()
            dob = request.POST.get("password").strip()

            student = Student.objects.filter(
                roll__iexact=roll,
                dob__iexact=dob
            ).first()

            if student:
                request.session["student"] = roll
                return redirect("view_seating")
            else:
                messages.error(request, "Invalid Roll No or DOB") 
                return redirect("view_seating")
        else:
            messages.error(request, "Invalid Roll No or DOB")

    return render(request, "login.html")

def redirect_after_login(request):
    if request.user.is_staff:
        return redirect('dashboard')
    else:
        return redirect('view_seating')

def logout_view(request):
    if request.user.is_authenticated:
        logout(request)

    if "student" in request.session:
        del request.session["student"]

    messages.success(request, "Logged out successfully!")
    return redirect('login')

@staff_member_required
def dashboard(request):
    school = School.objects.filter(admin=request.user.username).first()
    school_id = school.code if school else None

    total_students = Student.objects.filter(school_id=school_id).count() if school_id else 0
    total_rooms = Room.objects.filter(school_id=school_id).count() if school_id else 0
    
    students = list(Student.objects.filter(school_id=school_id).values())
    rooms = list(Room.objects.filter(school_id=school_id).values())

    for s in students:
        s["id"] = s["id"]
    for r in rooms:
        r["id"] = r["id"]

    context = {
        'total_students': total_students,
        'total_rooms': total_rooms,
        'students': students,
        'rooms': rooms
    }
    return render(request, "dashboard.html", context)

@staff_member_required
def add_student(request):
    if request.method == "POST":
        roll = request.POST.get("roll", "").strip()
        name = request.POST.get("name", "").strip()
        course = request.POST.get("course", "").strip()
        subject = request.POST.get("subject", "").strip()
        year_sem = request.POST.get("year_sem", "").strip()
        dob = request.POST.get("dob", "").strip()
        
        school = School.objects.filter(admin=request.user.username).first()
        school_id = school.code if school else None

        if Student.objects.filter(roll=roll, school_id=school_id).exists():
            messages.error(request, "Student with this Roll Number already exists in this school!")
            return redirect("add_student")

        Student.objects.create(
            roll=roll,
            name=name,
            course=course,
            subject=subject,
            year_sem=year_sem,
            dob=dob,
            school_id=school_id
        )

        if not User.objects.filter(username=roll).exists():
            user = User.objects.create_user(username=roll)
            user.set_password(dob)   
            user.save()

        messages.success(request, "Student added successfully!")
        return redirect("dashboard")
    
    return render(request, "add_student.html")

@staff_member_required
def update_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == "POST":
        roll = request.POST.get("roll", "").strip()
        name = request.POST.get("name", "").strip()
        course = request.POST.get("course", "").strip()
        subject = request.POST.get("subject", "").strip()
        year_sem = request.POST.get("year_sem", "").strip()
        dob = request.POST.get("dob", "").strip()
        old_roll = student.roll

        student.roll = roll
        student.name = name
        student.course = course
        student.subject = subject
        student.year_sem = year_sem
        student.dob = dob
        student.save()

        if User.objects.filter(username=old_roll).exists():
            user = User.objects.get(username=old_roll)
            user.username = roll     
            user.set_password(dob)   
            user.save()

        messages.success(request, "Student updated successfully")
        return redirect("dashboard")
    
    student_dict = {
        "id": student.id,
        "roll": student.roll,
        "name": student.name,
        "course": student.course,
        "subject": student.subject,
        "year_sem": student.year_sem,
        "dob": student.dob
    }
    return render(request, "update_student.html", {"student": student_dict})

@staff_member_required
def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    roll = student.roll
    student.delete()
    
    if User.objects.filter(username=roll).exists():
        User.objects.get(username=roll).delete()

    return redirect("dashboard")

@staff_member_required
def upload_students(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        admin_username = request.user.username

        school = School.objects.filter(admin=admin_username).first()

        if not school:
            messages.error(request, "School not found")
            return redirect("dashboard")

        school_id = school.code

        if not file:
            messages.error(request, "No file uploaded")
            return redirect("upload_students")

        try:
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            elif file.name.endswith(".xlsx"):
                df = pd.read_excel(file)
            else:
                messages.error(request, "Only CSV/Excel allowed")
                return redirect("upload_students")

            # 🔥 Column names को clean करें (spaces हटाएं और lowercase करें)
            df.columns = df.columns.astype(str).str.strip().str.lower()

            added = 0
            skipped = 0

            for _, row in df.iterrows():
                roll = str(row.get("roll", "")).split(".")[0].strip() 

                if not roll or roll == "nan" or roll == "none":
                    skipped += 1
                    continue

                course_val = str(row.get("course", "")).strip()
                year_sem_val = str(row.get("year_sem", "")).strip()

                if Student.objects.filter(
                    roll=roll, 
                    school_id=school_id, 
                    course=course_val, 
                    year_sem=year_sem_val
                ).exists():
                    skipped += 1
                    continue

                dob_raw = row.get("dob")
                try:
                    if pd.notna(dob_raw):
                        dob = pd.to_datetime(dob_raw).strftime("%d-%m-%Y")
                    else:
                        dob = ""
                except:
                    dob = str(dob_raw).strip()

                Student.objects.create(
                    roll=roll,
                    name=str(row.get("name", "")).strip(),
                    course=course_val,
                    subject=str(row.get("subject", "")).strip(),
                    year_sem=year_sem_val,
                    dob=dob,
                    school_id=school_id
                )
                added += 1

            messages.success(
                request,
                f"{added} students added in {school_id}, {skipped} skipped"
            )

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

        return redirect("upload_students")

    return render(request, "upload_students.html")
@staff_member_required
def add_room(request):
    if request.method == "POST":
        school = School.objects.filter(admin=request.user.username).first()
        
        if not school:
            school_id = request.user.username.upper()
            School.objects.create(
                name=f"{request.user.username}'s School",
                admin=request.user.username,
                code=school_id
            )
        else:
            school_id = school.code
            
        total_rows = int(request.POST.get("total_rows", 1))
        total_columns = int(request.POST.get("total_columns", 1))
        seats_per_bench = int(request.POST.get("seats_per_bench", 2))
        capacity = total_rows * total_columns * seats_per_bench

        Room.objects.create(
            room_no=request.POST.get("room_no"),
            capacity=capacity,
            seats_per_bench=seats_per_bench,
            total_rows=total_rows,
            total_columns=total_columns,
            building_name=request.POST.get("building_name"),
            floor_number=int(request.POST.get("floor_number", 0)),
            room_type=request.POST.get("room_type"),
            school_id=school_id   
        )
        
        messages.success(request, "Room added successfully! ✅")
        return redirect("dashboard")
        
    return render(request, "add_room.html")

@staff_member_required
def update_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    
    if request.method == "POST":
        room.room_no = request.POST.get("room_no")
        total_rows = int(request.POST.get("total_rows"))
        total_columns = int(request.POST.get("total_columns"))
        seats_per_bench = int(request.POST.get("seats_per_bench", 2))
        room.total_rows = total_rows
        room.total_columns = total_columns
        room.seats_per_bench = seats_per_bench
        room.capacity = total_rows * total_columns * seats_per_bench
        room.building_name = request.POST.get("building_name")
        room.floor_number = int(request.POST["floor_number"])
        room.room_type = request.POST.get("room_type")
        room.save()

        return redirect("dashboard")

    room_dict = {
        "id": room.id,
        "room_no": room.room_no,
        "capacity": room.capacity,
        "seats_per_bench": room.seats_per_bench,
        "total_rows": room.total_rows,
        "total_columns": room.total_columns,
        "building_name": room.building_name,
        "floor_number": room.floor_number,
        "room_type": room.room_type
    }
    return render(request, "update_room.html", {"room": room_dict})

@staff_member_required
def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    room.delete()
    return redirect("dashboard")

@staff_member_required
def download_pdf(request):
    seating = list(Seating.objects.all().values())

    if not seating:
        return HttpResponse("No seating data found")
    generate_pdf(seating)

    return FileResponse(open("Seating_Arrangement.pdf", "rb"), as_attachment=True)

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

    selected_date = request.POST.get("date")
    start_time = request.POST.get("start_time")
    start_ampm = request.POST.get("start_ampm")
    end_time = request.POST.get("end_time")
    end_ampm = request.POST.get("end_ampm")

    buildings = [b.strip() for b in request.POST.getlist("building[]")]
    floors = [int(f) for f in request.POST.getlist("floor[]")]
    room_types = [r.strip() for r in request.POST.getlist("room_type[]")]

    alerts = []

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

    start_time_24 = convert_to_24hr(start_time, start_ampm)
    end_time_24 = convert_to_24hr(end_time, end_ampm)
    display_time = f"{start_time} {start_ampm} - {end_time} {end_ampm}"

    school = School.objects.filter(admin=request.user.username).first()

    if not school:
        messages.error(request, "⚠️ School not found")
        return redirect("school_settings")

    school_id = school.code

    students = list(Student.objects.filter(school_id=school_id).values())
    if not students:
        return render(request, "seating.html", {
            "seating": [],
            "alerts": ["No students found"]
        })

    rooms = list(Room.objects.filter(
        school_id=school_id, 
        building_name__in=buildings,
        floor_number__in=floors,
        room_type__in=room_types
    ).values())

    if not rooms:
        return render(request, "seating.html", {
            "seating": [],
            "alerts": ["No rooms found for selected filters"]
        })

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

    rooms = sorted(
        unique_rooms,
        key=lambda r: (
            r.get("building_name", ""),
            r.get("floor_number", ""),
            r.get("room_no", ""),
            r.get("room_type", "")
        )
    )

    seating_results, gen_alerts = generate_seating(
        students,
        rooms,
        selected_date,
        start_time_24,
        end_time_24
    )

    alerts.extend(gen_alerts)

    for s in seating_results:
        s["display_time"] = display_time
        s["school_id"] = school_id   

    Seating.objects.filter(school_id=school_id).delete()

    if seating_results:
        seating_objects = [Seating(**item) for item in seating_results]
        Seating.objects.bulk_create(seating_objects)

    try:
        conflict_alerts = detect_conflicts(seating_results)
        alerts.extend(conflict_alerts)
    except Exception as e:
        alerts.append(f"Conflict check failed: {str(e)}")

    try:
        generate_pdf(seating_results)
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

    if is_teacher:
        school = School.objects.filter(admin=request.user.username).first()
        school_id = school.code if school else None

        seating_qs = Seating.objects.filter(school_id=school_id)

        if query and query.strip():
            seating_qs = seating_qs.filter(
                Q(roll__iexact=query.strip()) | Q(name__icontains=query.strip())
            )

        if exam_date:
            seating_qs = seating_qs.filter(exam_date=exam_date)
            
        seating = list(seating_qs.order_by(
            "course", "year_sem", "exam_date", "start_time", "room_no", "row", "column"
        ).values())

        if not seating:
            return render(request, "seating.html", {
                "seating": [],
                "is_admin": True
            })

        for s in seating:
            s["course"] = s.get("course", "").strip().upper()
            s["year_sem"] = s.get("year_sem", "").strip().upper()
            s["group"] = f"{s['course']} - {s['year_sem']}"

        return render(request, "seating.html", {
            "seating": seating,
            "is_admin": True
        })

    else:
        roll = request.session.get("student")

        if not roll:
            return redirect("login")

        seat = Seating.objects.filter(roll__iexact=str(roll).strip()).order_by("-id").values().first()

        if seat and not seat.get("display_time"):
            start = seat.get("start_time", "")
            end = seat.get("end_time", "")
            seat["display_time"] = f"{start} - {end}"

        school = {}
        if seat and seat.get("school_id"):
            school = School.objects.filter(code=seat["school_id"]).values().first() or {}

        return render(request, "seating.html", {
            "seat": seat,
            "is_admin": False,
            "school_logo": school.get("logo"),
            "school_name": school.get("name")
        })

@login_required
def school_settings(request):
    if not request.user.is_staff:
        return redirect("dashboard")
    
    school = School.objects.filter(admin=request.user.username).first()
    school_dict = {"name": school.name, "logo": school.logo, "code": school.code} if school else {}

    if request.method == "POST":
        name = request.POST.get("school_name")
        logo = request.FILES.get("logo")

        if not school:
            school = School(admin=request.user.username, code=request.user.username.upper())

        school.name = name

        if logo:
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            filename = str(int(time.time())) + "_" + logo.name
            file_path = os.path.join(settings.MEDIA_ROOT, filename)

            with open(file_path, 'wb+') as f:
                for chunk in logo.chunks():
                    f.write(chunk)
            
            if school.logo:
                old_path = os.path.join(settings.MEDIA_ROOT, str(school.logo))
                if os.path.exists(old_path):
                    os.remove(old_path)

            school.logo = filename

        school.save()

        messages.success(request, "✅ School settings updated successfully!")
        return redirect("school_settings")

    return render(request, "school_settings.html", {"school": school_dict})