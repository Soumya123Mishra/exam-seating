
from datetime import datetime

def detect_conflicts(seating):
    alerts = []

    for i in range(len(seating)):
        for j in range(i + 1, len(seating)):

            s1 = seating[i]
            s2 = seating[j]

            # Nearby seat check
            if (
                s1["room_no"] == s2["room_no"] and
                abs(s1["row"] - s2["row"]) <= 1 and
                abs(s1["column"] - s2["column"]) <= 1
            ):

                risk_score = 0
                reasons = []

                # 1. Same subject
                if s1["subject"] == s2["subject"]:
                    risk_score += 10
                    reasons.append("Same Subject")

                # 2. Same semester
                if s1.get("year_sem") == s2.get("year_sem"):
                    risk_score += 5
                    reasons.append("Same Semester")

                # 3. Consecutive roll numbers
                try:
                    roll1 = int(s1["roll"])
                    roll2 = int(s2["roll"])

                    if abs(roll1 - roll2) <= 1:
                        risk_score += 3
                        reasons.append("Adjacent Roll No")
                except:
                    pass

                # Only alert for medium/high risk
                if risk_score >= 10:

                    alert_text = (
                        f"Room {s1['room_no']} | "
                        f"Seat {s1['bench_no']} & {s2['bench_no']} | "
                        f"Risk {risk_score}"
                    )

                    

                    alerts.append(
                        f"⚠ High Risk Conflict | "
                        f"{alert_text} | "
                        f"Reason: {', '.join(reasons)} | "
                       
                    )

   
    if not alerts:
        alerts.append("✅ No conflicts detected")

    return alerts