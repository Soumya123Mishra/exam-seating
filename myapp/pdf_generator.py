from fpdf import FPDF
from collections import defaultdict

def get_roll_range(rolls):
    valid_rolls = []
    for r in rolls:
        if r is not None and str(r).strip().isdigit():
            valid_rolls.append(int(str(r).strip()))
            
    if not valid_rolls:
        return ""
        
    valid_rolls = sorted(list(set(valid_rolls)))
    
    if len(valid_rolls) == 1:
        return str(valid_rolls[0])
    
    ranges = []
    start = valid_rolls[0]
    end = valid_rolls[0]
    
    for i in range(1, len(valid_rolls)):
        if valid_rolls[i] == end + 1:
            end = valid_rolls[i]
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = valid_rolls[i]
            end = valid_rolls[i]
            
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
        
    return ", ".join(ranges)

def generate_pdf(seating):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    room_groups = defaultdict(list)
    for s in seating:
        key = (s.get("building_name"), s.get("floor_number"), s.get("room_no"), s.get("room_type"))
        room_groups[key].append(s)

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Exam Seating Arrangement Summary", 0, 1, 'C')
    pdf.ln(5)

    for room_key, records in room_groups.items():
        building, floor, room_no, room_type = room_key
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"Building: {building} | Floor: {floor} | Room: {room_no} ({room_type})", 0, 1, 'L')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(30, 8, "Bench", 1, 0, 'C')
        pdf.cell(30, 8, "Position", 1, 0, 'C')
        pdf.cell(40, 8, "Roll No", 1, 0, 'C')
        pdf.cell(60, 8, "Student Name", 1, 0, 'C')
        pdf.cell(50, 8, "Course / Sem", 1, 0, 'C')
        pdf.cell(50, 8, "Subject", 1, 1, 'C')

        pdf.set_font("Arial", size=9)
        for rec in records:
            pdf.cell(30, 7, str(rec.get("bench_label", "")), 1, 0, 'C')
            pdf.cell(30, 7, str(rec.get("position", "")), 1, 0, 'C')
            pdf.cell(40, 7, str(rec.get("roll", "")), 1, 0, 'C')
            pdf.cell(60, 7, str(rec.get("name", "")), 1, 0, 'C')
            pdf.cell(50, 7, f"{rec.get('course', '')} {rec.get('year_sem', '')}", 1, 0, 'C')
            pdf.cell(50, 7, str(rec.get("subject", "")), 1, 1, 'C')
        pdf.ln(5)

    pdf.output("Seating_Arrangement.pdf")