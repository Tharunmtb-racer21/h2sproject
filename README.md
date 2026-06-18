# 🏥 Queue Cure '26

### Transforming Clinic Queue Management Through Real-Time Technology
🔊 AI Voice Announcements • ⚡ Real-Time Updates • ⏱ Smart Wait Time Estimation

> "No more paper tokens. No more uncertainty. No more waiting without visibility."

## 🚀 Live Demo

🌐 Live Application:
https://tharuns-h2sproject.vercel.app/

## 🏆 Highlights

* ⚡ Real-Time Queue Synchronization
* 🔊 AI Voice Announcements
* ⏱ Dynamic Wait-Time Calculation
* 🏥 Receptionist Dashboard
* 📱 Public Display Dashboard
* 🚫 No Page Refresh Required

Queue Cure transforms traditional paper-token systems into a smart, transparent, and accessible clinic queue management platform.


---

## 📌 The Problem

76% of India's clinics still rely on paper token systems and manual queue management.

Patients often:

* Wait for hours without knowing when they will be called
* Continuously ask receptionists about their turn
* Experience frustration due to lack of visibility

Receptionists:

* Manage queues manually
* Handle token distribution
* Answer repetitive queue-related questions

This results in inefficiency, confusion, and poor patient experience.

---

## 💡 Our Solution

Queue Cure is a real-time hospital queue management system that brings transparency to clinic waiting rooms.

The platform enables:

✅ Receptionists to manage queues efficiently

✅ Patients to track their position in real time

✅ Instant queue updates across all connected screens

✅ Smart waiting time estimation

✅ AI Voice Announcements

---

## 🔊 What Makes Queue Cure Different?

### AI Voice Announcement System

Queue Cure automatically announces the next patient using AI-powered speech synthesis when the receptionist clicks "Call Next".

Example:

"Token Number 105, Arun Kumar, kindly proceed to meet the doctor."

Benefits:

* Reduces receptionist workload
* Improves patient awareness
* Helps patients who are not constantly watching the display
* Creates a smart-clinic experience
* Improves accessibility for patients

Unlike traditional token systems, Queue Cure actively communicates queue progress to patients through automated voice announcements.

---

## ✨ Key Features

### Receptionist Dashboard

* Add Patient
* Automatic Token Generation
* Call Next Patient
* Set Consultation Duration

### 📱 Public Display Dashboard

* Current Token Display
* Tokens Ahead
* Estimated Waiting Time
* Live Queue Tracking
* AI Voice Announcements

### Real-Time Synchronization

The moment the receptionist clicks:

"Call Next"
AI Voice Announcements

every connected patient screen updates instantly.

No refresh required.

---

## ⚡ Real-Time Queue Flow & Socket Event Diagram

Receptionist Dashboard
│
▼
Call Next
│
▼
Backend
│
▼
Socket.IO
│
▼
Public Display Dashboard
│
▼
AI Voice Announcement

Every queue update is broadcast instantly to all connected screens without requiring a page refresh.


---

## ⏱ Smart Wait Time Estimation

Queue Cure dynamically calculates waiting time using queue position and average consultation duration.

Example:

Current Token: 102

Your Token: 105

Tokens Ahead: 3

Average Consultation Time: 10 Minutes

Estimated Wait: 30 Minutes

No hardcoded values are used.

---

## 🛠 Tech Stack

Frontend

* React
* Tailwind CSS

Backend

* Node.js
* Express.js

Database

* MongoDB

Real-Time Communication

* Socket.IO

Deployment

* Vercel

---

## 📸 Project Screenshots

### Receptionist Dashboard

<img width="1423" height="771" alt="image" src="https://github.com/user-attachments/assets/2244de48-c516-4997-9fb2-4710f6e51bb4" />
<img width="1425" height="766" alt="image" src="https://github.com/user-attachments/assets/535d4c64-b658-4041-82ac-690292f355e7" />
<img width="1400" height="766" alt="image" src="https://github.com/user-attachments/assets/c01c506c-63fa-4fb6-b10b-491b3a4363cc" />




### Patient Waiting Room

<img width="1425" height="762" alt="image" src="https://github.com/user-attachments/assets/b2217dc9-9cf1-4ea8-984a-163f8e715a4b" />
<img width="1413" height="761" alt="image" src="https://github.com/user-attachments/assets/9106e762-f404-45cb-868f-c96b5a840460" />


## 🎥 Demo Video

Watch Queue Cure in action:

👉 https://youtu.be/Mz9ICOahzC8

Features Demonstrated:
- Patient Registration
- Automatic Token Generation
- AI Voice Announcements
- Real-Time Queue Synchronization
- Smart Wait-Time Estimation

Example Announcement:

"Token Number 105, Arun Kumar, kindly proceed to meet the doctor."

Benefits:

* Improves patient awareness
* Reduces receptionist workload
* Helps patients who are not constantly watching the display
* AI Voice Announcements
* Creates a real hospital-like queue experience

This feature enhances accessibility and improves overall patient flow management.

---

## 🧠 Edge Cases Considered

## 📝 Thought Process

The goal of Queue Cure was to eliminate uncertainty in clinic waiting rooms while reducing receptionist workload.

Key Design Decisions:

* Real-time synchronization to ensure all displays remain updated
* Dynamic wait-time calculation based on consultation duration
* AI voice announcements to improve accessibility and patient awareness
* Simple receptionist workflow to minimize operational errors

Challenges Considered:

* Multiple users viewing the queue simultaneously
* Queue consistency after page refresh
* Empty queue handling
* Real-time update delivery
* Future scalability for multi-clinic environments
---

## 🔮 Future Enhancements

* SMS Notifications
* Doctor Dashboard
* Appointment Booking
* Queue Analytics
* Multi-Clinic Support

---

## 👨‍💻 Developed By

Tharun N E 

Queue Cure '26 Hackathon Submission
