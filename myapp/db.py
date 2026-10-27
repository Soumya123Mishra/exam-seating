from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["exam_db"]

admin_col = db["admin"]
students_col = db["students"]
rooms_col=db["rooms"]
exam_col = db["exams"]
seating_col = db["seating"]
schools_col = db["schools"]