from fpdf import FPDF
from datetime import datetime
from collections import defaultdict


def get_roll_range(rolls):
   
    if not rolls:
        return "-"

    rolls = sorted(set(int(r) for r in rolls))

    ranges = []
    start = rolls[0]
    end = rolls[0]

    for i in range(1, len(rolls)):
        if rolls[i] == end + 1:
            end = rolls[i]
        else:
            ranges.append(f"{start}-{end}" if start != end else str(start))
            start = end = rolls[i]

    ranges.append(f"{start}-{end}" if start != end else str(start))

    return "Roll No. " + ", ".join(ranges)


def generate_pdf(seating):

    if not seating:
        return

    #  REMOVE DUPLICATES 
    unique_data = []
    seen = set()

    for s in seating:
        key = (
            s.get("room_no"),
            s.get("row"),
            s.get("column"),
            s.get("roll"),
            s.get("course"),
            s.get("year_sem")
        )
        if key not in seen:
            seen.add(key)
            unique_data.append(s)

    seating = unique_data

    #  SORT 
    seating = sorted(
        seating,
        key=lambda x: (
            x.get("room_no", ""),
            x.get("row", 0),
            x.get("column", 0)
        )
    )

    pdf = FPDF("L", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    first = seating[0]

    #  TITLE 
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "SEATING PLAN EXAMINATION", ln=True, align="C")

    #  DATE + TIME
    pdf.set_font("Arial", "B", 10)

    date = first.get("exam_date", "-")
    time = first.get(
        "display_time",
        f"{first.get('start_time', '')} - {first.get('end_time', '')}"
    )

    pdf.cell(140, 8, f"DATE: {date}", 0, 0, "L")
    pdf.cell(140, 8, f"TIME: {time}", 0, 1, "R")

    pdf.ln(4)

    #  GROUP BY ROOM 
    room_groups = defaultdict(list)

    for s in seating:
        room_key = (
            s.get("building_name"),
            s.get("floor_number"),
            s.get("room_no"),
            s.get("room_type")
        )
        room_groups[room_key].append(s)

    #  ROOM LOOP
    for room_key, students in room_groups.items():

        building, floor, room_no, room_type = room_key

        # Room heading
        pdf.set_font("Arial", "B", 9)
        pdf.cell(
            0,
            8,
            f"Building: {building} | Floor: {floor} | Room: {room_no} | Type: {room_type}",
            1,
            1,
            "C"
        )

        pdf.ln(2)

        #  GROUP BY COURSE 
        course_groups = defaultdict(list)

        for s in students:
            course_name = f"{s.get('course')} ({s.get('year_sem')})"
            course_groups[course_name].append(s)

        courses = sorted(course_groups.keys())

        page_width = 277
        row_width = 20
        col_width = (page_width - row_width) / max(len(courses), 1)

        #  TABLE HEADER
        pdf.set_font("Arial", "B", 9)
        pdf.cell(row_width, 8, "Row", 1, 0, "C")

        for course in courses:
            pdf.cell(col_width, 8, course[:22], 1, 0, "C")

        pdf.ln()

        max_row = max(s.get("row", 1) for s in students)

        # ROW SUMMARY 
        for row_num in range(1, max_row + 1):

            # Auto new page
            if pdf.get_y() > 180:
                pdf.add_page()

            pdf.set_font("Arial", "B", 8)
            pdf.cell(row_width, 8, f"Row {row_num}", 1, 0, "C")

            for course in courses:

                row_students = [
                    s for s in course_groups[course]
                    if s.get("row") == row_num
                ]

                rolls = [s.get("roll") for s in row_students]

                cell_text = get_roll_range(rolls)
                

                pdf.set_font("Arial", "", 8)
                pdf.cell(col_width, 8, cell_text, 1, 0, "C")

            pdf.ln()

        pdf.ln(4)

    # NOTES 
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 8, "NOTE:", ln=True)

    pdf.set_font("Arial", "", 8)
    pdf.multi_cell(
        0,
        5,
        "1. Bags and mobile phones are not allowed.\n"
        "2. Students must sit on assigned seats only.\n"
        "3. Reach exam hall 30 minutes before exam."
    )

    #FOOTER 
    pdf.ln(2)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(
        0,
        6,
        f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
        ln=True,
        align="R"
    )

    pdf.output("Seating_Arrangement.pdf")