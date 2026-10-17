import random
from collections import defaultdict, deque


def normalize(text):
    return str(text).strip().upper()


def calculate_risk_score(student, nearby_keys, nearby_rolls):
    score = 0

    current_key = (
        student["subject"],
        student["course"],
        student["year_sem"]
    )

    if current_key in nearby_keys:
        score += 10
    try:
        roll = int(student.get("roll", 0))
        for r in nearby_rolls:
            if abs(roll - r) <= 1:
                score += 5
    except:
        pass

    return score


def generate_seating(
    students,
    rooms,
    selected_date,
    start_time,
    end_time
):
    alerts = []
    conflict_tracker = defaultdict(int)
    # 1️⃣ Validation
    
    if not students:
        return [], ["No students available."]

    if not rooms:
        return [], ["No rooms available."]

    for s in students:
        s["subject"] = normalize(
            s.get("subject", "UNKNOWN")
        )
        s["course"] = normalize(
            s.get("course", "")
        )
        s["year_sem"] = normalize(
            s.get("year_sem")
            or s.get("year_semester")
            or ""
        )
    #  Capacity Check
   
    total_capacity = sum(
        int(r.get("capacity", 0))
        for r in rooms
    )

    if len(students) > total_capacity:
        alerts.append(
            "⚠ Not enough seats available!"
        )
    groups = defaultdict(list)

    for s in students:
        key = (
            s["subject"],
            s["course"],
            s["year_sem"]
        )
        groups[key].append(s)

    for key in groups:
        random.shuffle(groups[key])

    queues = [deque(v) for v in groups.values()]
    mixed_students = []

    while any(queues):
        for q in queues:
            if q:
                mixed_students.append(
                    q.popleft()
                )

   # Seat Allocation
   
    seating = []
    index = 0
    seat_map = {}

    for room in rooms:

        columns = int(
            room.get("total_columns", 5)
        )
        rows = int(
            room.get("total_rows", 3)
        )

        seats_per_bench = int(
            room.get("seats_per_bench", 2)
        )

        capacity = int(
            room.get("capacity", 0)
        )

        if capacity <= 0:
            continue

        total_benches = (
            capacity // seats_per_bench
        )

        room_no = room.get("room_no")

        room_key = (
            room.get("building_name"),
            room.get("floor_number"),
            room_no,
            room.get("room_type")
        )

        bench_counter = 1

        for bench in range(total_benches):

            if index >= len(mixed_students):
                break

            row = bench // columns + 1
            column = bench % columns + 1

            if row > rows:
                alerts.append(
                    f"⚠ Room {room_no} layout exceeded "
                    f"({rows} × {columns})"
                )
                break

            for seat_pos in range(
                seats_per_bench
            ):

                if index >= len(
                    mixed_students
                ):
                    break

                # Nearby seats
                same_bench_left = seat_map.get(
                    (
                        room_key,
                        row,
                        column,
                        "Left"
                    )
                )

                same_bench_right = seat_map.get(
                    (
                        room_key,
                        row,
                        column,
                        "Right"
                    )
                )

                front_left = seat_map.get(
                    (
                        room_key,
                        row - 1,
                        column,
                        "Left"
                    )
                )

                front_right = seat_map.get(
                    (
                        room_key,
                        row - 1,
                        column,
                        "Right"
                    )
                )

                nearby_keys = [
                    same_bench_left,
                    same_bench_right,
                    front_left,
                    front_right
                ]

                nearby_rolls = []

                for seat in seating:
                    if (
                        seat["room_no"]
                        == room_no
                        and abs(
                            seat["row"] - row
                        ) <= 1
                        and abs(
                            seat["column"]
                            - column
                        ) <= 1
                    ):
                        try:
                            nearby_rolls.append(
                                int(
                                    seat["roll"]
                                )
                            )
                        except:
                            pass

                # AI best candidate
                best_student = (
                    mixed_students[index]
                )
                best_score = float("inf")
                best_index = index

                search_limit = min(
                    index + 5,
                    len(mixed_students)
                )

                for i in range(
                    index,
                    search_limit
                ):
                    candidate = (
                        mixed_students[i]
                    )

                    score = (
                        calculate_risk_score(
                            candidate,
                            nearby_keys,
                            nearby_rolls
                        )
                    )

                    if score < best_score:
                        best_score = score
                        best_student = candidate
                        best_index = i

                
                mixed_students[index], mixed_students[
                    best_index
                ] = (
                    mixed_students[
                        best_index
                    ],
                    mixed_students[index]
                )

                student = (
                    mixed_students[index]
                )

                current_key = (
                    student["subject"],
                    student["course"],
                    student["year_sem"]
                )

                # Position
                if seats_per_bench == 1:
                    position = "Single"
                else:
                    position = (
                        "Left"
                        if seat_pos == 0
                        else "Right"
                    )

                # Conflict summary
                if current_key in nearby_keys:
                    conflict_tracker[
                        room_no
                    ] += 1

                seating.append({
                    "room": room_no,
                    "room_no": room_no,
                    "row": row,
                    "column": column,
                    "bench_no": (
                        f"R{row}C{column}"
                    ),
                    "bench_label": (
                        f"Bench {bench_counter}"
                    ),
                    "position": position,
                    "roll": str(
                        student.get("roll")
                    ),
                    "name": student.get(
                        "name"
                    ),
                    "subject": student.get(
                        "subject"
                    ),
                    "course": student.get(
                        "course"
                    ),
                    "year_sem": student.get(
                        "year_sem"
                    ),
                    "exam_date": selected_date,
                    "start_time": start_time,
                    "end_time": end_time,
                    "building_name": room.get(
                        "building_name"
                    ),
                    "floor_number": room.get(
                        "floor_number"
                    ),
                    "room_type": room.get(
                        "room_type"
                    ),
                })

                seat_map[
                    (
                        room_key,
                        row,
                        column,
                        position
                    )
                ] = current_key

                index += 1

            bench_counter += 1

   # Alerts
    
    if len(students) < total_capacity:
        alerts.append(
            "ℹ Some seats are empty."
        )

    if index < len(students):
        alerts.append(
            "⚠ Some students could not be seated."
        )

    # Room-wise conflict
    for room_no, count in (
        conflict_tracker.items()
    ):
        alerts.append(
            f"⚠ Room {room_no}: "
            f"{count} possible conflict(s)"
        )

    
    alerts = list(
        dict.fromkeys(alerts)
    )
    alerts = alerts[:5]

    return seating, alerts