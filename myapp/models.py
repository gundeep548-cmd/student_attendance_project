from django.db import models

# Create your models here.
class Student(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    roll = models.CharField(max_length=50, null= True , blank=True)
    course = models.CharField(max_length=100)
    image = models.ImageField(upload_to='student_photos/', null=True, blank=True)

    def __str__(self):
        return self.name


class Attendance(models.Model):
    student= models.ForeignKey(Student, on_delete=models.CASCADE)
    date= models.DateField(auto_now_add=True)
    time= models.TimeField(auto_now_add=True)
    status= models.CharField(max_length=10, default="Present")

    def __str__(self):
        return f"{self.student.name} - {self.date}"        