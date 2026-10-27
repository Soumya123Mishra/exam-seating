from django.db import models
from django.contrib.auth.models import User

class School(models.Model):
    name = models.CharField(max_length=255)
    admin = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)

    def __str__(self):
        return self.name

class Student(models.Model):
    roll = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    course = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    year_sem = models.CharField(max_length=50)
    dob = models.CharField(max_length=50)
    school_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.roll} - {self.name}"

class Room(models.Model):
    room_no = models.CharField(max_length=50)
    capacity = models.IntegerField()
    seats_per_bench = models.IntegerField(default=2)
    total_rows = models.IntegerField()
    total_columns = models.IntegerField()
    building_name = models.CharField(max_length=100)
    floor_number = models.IntegerField(default=0)
    room_type = models.CharField(max_length=50)
    school_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Room {self.room_no} ({self.building_name})"

class Seating(models.Model):
    roll = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    course = models.CharField(max_length=100)
    subject = models.CharField(max_length=100, blank=True, null=True)
    year_sem = models.CharField(max_length=50)
    exam_date = models.CharField(max_length=50, blank=True, null=True)
    start_time = models.CharField(max_length=20, blank=True, null=True)
    end_time = models.CharField(max_length=20, blank=True, null=True)
    display_time = models.CharField(max_length=100, blank=True, null=True)
    building_name = models.CharField(max_length=100, blank=True, null=True)
    floor_number = models.IntegerField(blank=True, null=True)
    room = models.CharField(max_length=50, blank=True, null=True)             # 🔥 नया फील्ड जोड़ा गया
    room_no = models.CharField(max_length=50, blank=True, null=True)
    room_type = models.CharField(max_length=50, blank=True, null=True)
    bench_no = models.CharField(max_length=50, blank=True, null=True)
    bench_label = models.CharField(max_length=50, blank=True, null=True)       # 🔥 नया फील्ड जोड़ा गया
    position = models.CharField(max_length=50, blank=True, null=True)         # 🔥 नया फील्ड जोड़ा गया
    row = models.IntegerField(blank=True, null=True)
    column = models.IntegerField(blank=True, null=True)
    school_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.roll} -> Room {self.room_no}"