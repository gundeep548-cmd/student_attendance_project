import json
import cv2
import os
import base64
import numpy as np
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Q
from .models import Student, Attendance

def started_page(request):
    return render(request, 'startedpage.html')  

def homepage(request):
    return render(request, 'homepage.html')

def login_page(request):
    return render(request, 'login.html')



def student_login_process(request):
    """Student ke Name aur Roll Number ko authenticate karne ka function"""
    if request.method == 'POST':
        input_name = request.POST.get('name', '').strip()
        input_roll = request.POST.get('roll', '').strip()

        try:
            
            student = Student.objects.get(name__iexact=input_name, roll=input_roll)
            
            
            request.session['logged_in_student_id'] = student.id
            return redirect('student_profile')
            
        except Student.DoesNotExist:
            
            messages.error(request, "Invalid Name or Roll Number! Please try again.")
            return redirect('login_page')
            
    return redirect('login_page')


def student_profile(request):
    
    student_id = request.session.get('logged_in_student_id')
    
    if not student_id:
        messages.error(request, "Please login first!")
        return redirect('login_page')
        
    student = get_object_or_404(Student, id=student_id)
    
    
    attendance_records = Attendance.objects.filter(student=student).order_by('-date')
    
    
    total_classes = Attendance.objects.values('date').distinct().count()
    present_count = attendance_records.filter(status='Present').count()
    
    percentage = (present_count / total_classes * 100) if total_classes > 0 else 0

    return render(request, 'student_profile.html', {
        'student': student,
        'attendance_records': attendance_records,
        'present_count': present_count,
        'total_classes': total_classes,
        'percentage': round(percentage, 2)
    })


def student_logout(request):
    """Student session clear karke logout karne ke liye"""
    if 'logged_in_student_id' in request.session:
        del request.session['logged_in_student_id']
    return redirect('homepage')


def add_student(request):
    return render(request, 'add_student.html')

@csrf_exempt
def save_student(request):
    if request.method == 'POST':
         try:
            data = json.loads(request.body)
            name = data.get('name')
            roll = data.get('roll')
            course = data.get('course')
            email = data.get('email')
            image_data = data.get('image')

            image_file = None
            if image_data and ';base64,' in image_data:
                format, imgstr = image_data.split(';base64,')
                ext = format.split('/')[-1]
                image_file = ContentFile(base64.b64decode(imgstr), name=f"{roll}.{ext}")

            Student.objects.create(
                name=name,
                roll=roll,
                course=course,
                image=image_file,
                email=email
            )
            return JsonResponse({'status': 'success', 'message': 'Data saved successfully!'})

         except Exception as e:
            print("Real error is here:", str(e))
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


def mark_attendance(request):
    """Dashboard ke 'Mark Attendance' button ke liye date filter view"""
    selected_date = request.GET.get('date')
    if not selected_date:
        selected_date = str(timezone.localdate())
        
    records = Attendance.objects.filter(date=selected_date)
    
    
    attendance_dict = {r.student_id: r.status for r in records}
    
    students = Student.objects.all()
    
    
    for student in students:
        student.current_status = attendance_dict.get(student.id, "No Log Found")

    return render(request, 'mark_attendance.html', {
        'students': students,
        'selected_date': selected_date
    })


def attendance_report(request):
    """Dashboard ke 'View Attendance Report' button ke liye view"""
    selected_date = request.GET.get('date')
    
    if selected_date:
        records = Attendance.objects.filter(date=selected_date).select_related('student')
    else:
        selected_date = str(timezone.localdate())
        records = Attendance.objects.filter(date=selected_date).select_related('student')
        
    students = Student.objects.all()

    return render(request, 'attendance_report.html', {
        'records': records, 
        'students': students,
        'selected_date': str(selected_date)
    })


def mark_attendance_manual(request, student_id):
    """Manual dropdown se attendance change karke mark karne ka logic"""
    if request.method == "POST":
        student = get_object_or_404(Student, id=student_id)
        selected_status = request.POST.get('status', 'Present') 
        today = timezone.localdate()

        attendance_record, created = Attendance.objects.get_or_create(
            student=student, 
            date=today,
            defaults={'status': selected_status}
        )

        if not created:
            attendance_record.status = selected_status
            attendance_record.save()

        return redirect('attendance_report')
    
    return redirect('homepage')


def view_students_attendance(request):
    """View All Attendance Percentages"""
    students = Student.objects.all()
    total_classes = Attendance.objects.values('date').distinct().count()
    
    student_data = []
    for student in students:
        present_count = Attendance.objects.filter(student=student, status='Present').count()
        
        if total_classes > 0:
            percentage = (present_count / total_classes) * 100
        else:
            percentage = 0
            
        student_data.append({
            'name': student.name,
            'roll': student.roll,
            'present_count': present_count,
            'total_classes': total_classes,
            'percentage': round(percentage, 2)
        })
    
    return render(request, 'view_students.html', {'student_data': student_data})


def gen_frames():
    cascade_name = 'haarcascade_frontalface_default.xml'
    cascade_path = os.path.join(cv2.__path__[0], 'data', cascade_name)
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    if face_cascade.empty():
        cascade_path = cv2.data.haarcascades + cascade_name
        face_cascade = cv2.CascadeClassifier(cascade_path)

    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
    except AttributeError:
        print("❌ CRITICAL ERROR")
        return

    students = Student.objects.all()
    faces_data = []
    labels = []
    student_dict = {}

    print("--- Training Started ---")

    for student in students:
        student_img_field = student.image if hasattr(student, 'image') else getattr(student, 'profile_pic', None)
        
        if student_img_field and student_img_field.name:
            image_path = student_img_field.path
            
            if os.path.exists(image_path):
                try:
                    student_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                    if student_img is None:
                        continue
                    
                    student_img = cv2.equalizeHist(student_img)
                    detected_faces = face_cascade.detectMultiScale(student_img, scaleFactor=1.2, minNeighbors=5)

                    for (x, y, w, h) in detected_faces:
                        face_roi = student_img[y:y+h, x:x+w]
                        face_roi_resized = cv2.resize(face_roi, (200, 200))

                        faces_data.append(face_roi_resized)
                        labels.append(student.id)
                        student_dict[student.id] = student
                        print(f"✅ Successfully trained face for: {student.name}")
                        break  
                        
                except Exception as e:
                    print(f"⚠️ Error processing image for {student.name}: {e}")

    is_trained = False
    if len(faces_data) > 0 and len(labels) > 0:
        try:
            recognizer.train(faces_data, np.array(labels))
            is_trained = True
            print(f"--- 🎉 Training Completed. Total Trained Students: {len(student_dict)} ---")
        except Exception as e:
            print(f"❌ Training failed: {e}")
    else:
        print("--- ⚠️ Training Failed: No faces found in database student images! ---")

    cap = cv2.VideoCapture(0)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray) 
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

            for (x, y, w, h) in faces:
                box_color = (0, 0, 255)  
                display_text = "No Student Found"
                matched_student = None
                confidence = 0

                if is_trained:
                    try:
                        face_roi = gray[y:y+h, x:x+w]
                        face_roi_resized = cv2.resize(face_roi, (200, 200))
                        label, confidence = recognizer.predict(face_roi_resized)

                        if confidence < 90:  
                            matched_student = student_dict.get(label)
                    except:
                        pass

                if matched_student:
                    try:
                        today = timezone.localdate()
                        already_marked = Attendance.objects.filter(student=matched_student, date=today).exists()

                        if not already_marked:
                            Attendance.objects.create(student=matched_student, date=today, status='Present')
                            box_color = (0, 255, 0)
                            display_text = f"{matched_student.name}: Marked"
                        else:    
                            box_color = (255, 255, 0)  
                            display_text = f"{matched_student.name}: Already Marked"
                    except Exception as e:
                        print(f"Attendance Error: {e}")
                        pass

                cv2.rectangle(frame, (x, y), (x+w, y+h), box_color, 2)
                cv2.putText(frame, f"{display_text} ({round(confidence)})", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
    except Exception as stream_error:
        print(f"❌ Streaming loop error: {stream_error}")
    finally:
        cap.release()

def camera_page(request):
    return render(request, 'camera_temp.html')

def start_camera(request):
    return StreamingHttpResponse(gen_frames(), content_type='multipart/x-mixed-replace; boundary=frame')
