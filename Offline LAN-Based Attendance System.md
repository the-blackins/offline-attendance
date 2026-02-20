# **Offline LAN-Based Attendance System**

## **1\. Purpose of This Document**

This document proposes a **clear implementation workflow and system architecture** for an offline / local-network-based school attendance system. It is intended for **technical experts or developers** who may take over, extend, or productionize the system in the future. The focus is on **continuity, scalability, and clarity of intent**, not just the MVP.

The system is designed to:

* Work **without internet access**
* Operate within a **shared local network (LAN)** hosted by a Raspberry Pi
* Enforce **one student → one device → one attendance record per session**
* **Sync attendance data to the cloud** when internet becomes available
* **Verify attendance** against a lecturer-managed course roster
* Support future upgrades (biometrics, analytics, university-wide deployment, etc.)

---

## **2\. Problem Context & Motivation**

Traditional attendance methods (manual roll-call, paper sheets, centralized online systems) suffer from:

* Time inefficiency
* Proxy attendance (impersonation)
* Dependence on internet connectivity
* Poor auditability

This project explores a **network-based presence verification model**, inspired by basic networking principles (shared subnet, device discovery, message passing), adapted into a structured and authenticated attendance workflow.

---

## **3\. Core Design Principles**

1. **Offline-first**: The system must work fully on a local network.
2. **Device-bound identity**: Attendance is tied to a registered device.
3. **Session-based validation**: Attendance is valid only during an active class session.
4. **Low friction for students**: Minimal steps during class time.
5. **Instructor authority**: Lecturer controls session lifecycle, overrides, and roster.
6. **Cloud-verified**: Attendance is verified against the course roster upon cloud sync.
7. **Extensibility**: Architecture must allow future modules without redesign.

---

## **4\. System Actors**

### **4.1 Students**

* Use a **phone or laptop** connected to the classroom network (Raspberry Pi hotspot)
* Authenticate once (enrollment)
* Perform a single tap/click per class to mark attendance

### **4.2 Lecturer / Host**

* Manages the **course roster** (registers students to courses via the cloud dashboard)
* Triggers session start/end via the **Arduino session controller**
* Views real-time attendance status on the **lecturer dashboard** (served by the Pi)
* Can **manually override** attendance (mark present/absent)

### **4.3 System (Hardware & Software Components)**

* **Arduino Uno** — session controller (physical buttons, LEDs, buzzer)
* **Raspberry Pi** — Wi-Fi hotspot + local server + database + cloud sync
* **PWA Client** — student and lecturer web interfaces
* **Cloud (Supabase)** — roster management, attendance verification, reporting

---

## **5\. System Architecture**

### **5.1 Hardware Architecture**

The system has three hardware layers and a cloud layer:

```
┌─────────────── CLASSROOM (Offline) ───────────────┐
│                                                    │
│   [Arduino Uno] ──USB Serial──▶ [Raspberry Pi]     │
│   Session Controller            Wi-Fi AP + Server  │
│   • Start/end buttons                              │
│   • LED indicators              [Student Phones]   │
│   • Buzzer feedback             connect via Wi-Fi  │
│                                                    │
└────────────────────────────────────────────────────┘
                        │
                        │ syncs when online
                        ▼
┌─────────────── CLOUD (Supabase) ──────────────────┐
│   • Lecturer accounts & auth                       │
│   • Course roster management                       │
│   • Synced attendance records                      │
│   • Verification engine (roster ↔ attendance)      │
│   • Attendance percentages & reports               │
│   • Admin dashboard                                │
└────────────────────────────────────────────────────┘
```

### **5.2 Network Layer**

* The Raspberry Pi acts as a **Wi-Fi access point (hotspot)**
* All student devices and the lecturer device connect to the Pi's hotspot
* Same subnet (e.g. 192.168.4.x)
* LAN communication only during class — no WAN dependency

### **5.3 Communication Model**

#### **Method A — WebSocket (Recommended for Production)**

* Persistent connection between client and Pi server
* Reliable delivery
* Real-time feedback
* Supports authentication and acknowledgements

#### **Method B — UDP Broadcast (Experimental / MVP)**

* Clients broadcast attendance packets
* Pi listens and buffers
* Lower reliability, minimal setup

The architecture favors **WebSocket for production**, UDP for early demos.

### **5.4 Arduino ↔ Raspberry Pi Communication**

The Arduino Uno communicates with the Pi via **USB Serial** (JSON protocol):

```
Arduino sends: {"action": "start_session", "course_code": "CSC301"}
Pi responds:   {"status": "ok", "session_id": "abc123"}

Arduino sends: {"action": "end_session", "session_id": "abc123"}
Pi responds:   {"status": "ok", "records": 42}
```

---

## **6\. Identity & Authentication Model**

Authentication is **layered**, not singular.

### **6.1 Student Identity**

* Student ID / matric number
* Optional PIN or password

### **6.2 Device Binding (Critical)**

* On first enrollment, client generates a **Device UUID**
* UUID is stored locally (localStorage + IndexedDB fallback) and sent to server
* Server binds:
  `student_id ↔ device_uuid`
* A student can only check in using the bound device
* **Re-enrollment** (new device) requires lecturer approval

### **6.3 Session Authentication**

* Each class creates a **session token**
* Token is time-bound and class-specific
* Distributed via:
  * QR code (with **time-rotating refresh** every 30 seconds)
  * LAN discovery

### **6.4 Validation Pipeline**

Every check-in is validated against ALL of the following:

1. Is the session currently active?
2. Is the session token valid?
3. Does the device UUID match the student's registered device?
4. Has the student already checked in for this session?

All four must pass → attendance recorded.

---

## **7\. Proposed Workflow**

### **7.1 Initial Enrollment (Once per Semester)**

1. Lecturer registers students to a course via the **cloud dashboard** (creates the roster)
2. Student connects to Pi's Wi-Fi hotspot
3. Opens client PWA
4. Enters student ID (+ optional PIN)
5. Client generates device UUID
6. Pi server validates and stores binding locally
7. Enrollment completed

This phase is controlled and supervised.

---

### **7.2 Attendance Session Workflow (Per Class)**

#### **Lecturer Actions (Arduino)**

1. Power on the Arduino + Pi setup in the classroom
2. Select course code on the Arduino (button/rotary encoder)
3. Press the **"Start Session"** button
4. Arduino signals the Pi via USB serial → Pi creates session
5. QR code / session info displayed on the lecturer dashboard
6. At end of class, press **"End Session"** → Pi locks session

#### **Student Actions**

1. Connect to Pi's Wi-Fi hotspot
2. Open client PWA
3. Tap "Check In"
4. Client sends: student\_id + device\_uuid + session\_token
5. Receives instant confirmation or rejection

#### **Server Validation**

* Session active? → Token valid? → Device matches? → Not already marked?
* If all pass → attendance recorded locally in SQLite

---

### **7.3 Buffering & Storage**

* Incoming attendance records are **immediately written to SQLite** (WAL mode for crash resilience)
* In-memory buffer maintained for fast real-time dashboard updates
* On session end: session is locked, records are finalized

This ensures resilience against crashes or sudden power loss.

---

### **7.4 Cloud Sync (Post-Session)**

1. Pi detects internet connectivity (periodic ping check)
2. Reads `sync_queue` table for pending records
3. Uploads attendance data to Supabase via REST API
4. Marks records as synced
5. Downloads updated roster for next session (pre-caching)

---

### **7.5 Cloud Verification**

Once attendance data is synced to the cloud:

1. Verification engine cross-references synced attendance against the **course roster**
2. If student is in the roster → **verified** → attendance percentage increases
3. If student is NOT in the roster → **flagged** → not counted
4. Lecturer can review flagged records and manually approve/reject

Two attendance metrics are maintained:
* **Raw percentage**: based on local check-ins
* **Verified percentage**: based on cloud-verified attendance

---

## **8\. Data Model**

### **Local Database (SQLite on Pi)**

#### **Students Table**
| Field | Type | Notes |
|-------|------|-------|
| id | INTEGER PK | Auto-increment |
| student_id | TEXT UNIQUE | Matric number |
| name | TEXT | Full name |
| device_uuid | TEXT UNIQUE | Bound device |
| enrolled_at | TIMESTAMP | Enrollment date |

#### **Sessions Table**
| Field | Type | Notes |
|-------|------|-------|
| id | INTEGER PK | Auto-increment |
| course_code | TEXT | e.g. CSC301 |
| session_token | TEXT UNIQUE | Time-bound token |
| start_time | TIMESTAMP | Session start |
| end_time | TIMESTAMP | Session end (null if active) |
| is_active | BOOLEAN | Quick lookup flag |

#### **Attendance Table**
| Field | Type | Notes |
|-------|------|-------|
| id | INTEGER PK | Auto-increment |
| student_id | FK → students | Who checked in |
| session_id | FK → sessions | Which session |
| timestamp | TIMESTAMP | When they checked in |
| status | TEXT | present / late / flagged |

#### **Sync Queue Table**
| Field | Type | Notes |
|-------|------|-------|
| id | INTEGER PK | Auto-increment |
| table_name | TEXT | Source table |
| record_id | INTEGER | Record to sync |
| status | TEXT | pending / synced / failed |
| synced_at | TIMESTAMP | When synced (null if pending) |

### **Cloud Database (Supabase / PostgreSQL)**

#### **Lecturers Table**
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | Supabase auth |
| name | TEXT | Full name |
| email | TEXT UNIQUE | Login credential |

#### **Courses Table**
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | Auto-generated |
| course_code | TEXT | e.g. CSC301 |
| course_name | TEXT | e.g. Operating Systems |
| lecturer_id | FK → lecturers | Course owner |

#### **Roster Table (Course Registrations)**
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | Auto-generated |
| course_id | FK → courses | Which course |
| student_id | TEXT | Matric number (matches local) |
| student_name | TEXT | Full name |
| registered_at | TIMESTAMP | When added to roster |

#### **Verified Attendance Table**
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | Auto-generated |
| student_id | TEXT | Matric number |
| course_code | TEXT | Course identifier |
| session_token | TEXT | Links to local session |
| check_in_time | TIMESTAMP | Original local timestamp |
| is_verified | BOOLEAN | Matched against roster? |
| synced_at | TIMESTAMP | When received from Pi |

---

## **9\. Security & Anti-Abuse Measures**

* **One device per student** enforcement via UUID binding
* **Session expiration** — tokens become invalid after session ends
* **Duplicate submission rejection** — server rejects if already marked
* **HMAC-signed payloads** — requests between client↔server and Arduino↔Pi are signed
* **Optional heartbeat** — periodic ping to verify student remains present during class
* **Manual override by lecturer** — mark a student present/absent regardless of check-in status
* **Rotating QR codes** — session QR refreshes every 30 seconds to prevent photo-sharing
* **Re-enrollment requires lecturer approval** — prevents unauthorized device swaps

Limitations are acknowledged (e.g. physical phone sharing), mitigated by supervision and device binding. The system prevents digital impersonation but cannot independently verify the physical identity of the device holder. Institutional supervision and optional biometric extensions mitigate this.

---

## **10\. Technology Stack**

| Component | Technology | Role |
|-----------|-----------|------|
| **Local Server** | Python + Flask + Flask-SocketIO | REST API + WebSocket server on the Pi |
| **Local Database** | SQLite (WAL mode) | Crash-resilient local storage |
| **Frontend** | PWA (HTML/CSS/JS) | Student + lecturer interfaces |
| **MCU Firmware** | Arduino C++ (PlatformIO) | Session controller on Arduino Uno |
| **Serial Bridge** | Python (pyserial) | Arduino ↔ Pi USB communication |
| **Cloud Database** | Supabase (PostgreSQL) | Roster, verified attendance, reports |
| **Cloud Sync** | Python background service | Detects internet, uploads pending records |
| **QR Generation** | Python `qrcode` library | Session token distribution |
| **Deployment** | Raspberry Pi (hostapd + systemd) | Wi-Fi AP + auto-start services |

---

## **11\. Microcontroller (MCU) Integration**

### **11.1 Rationale for MCU Integration**

To strengthen system reliability, physical presence validation, and long-term scalability, this system incorporates a **microcontroller-based classroom node** as part of the core architecture.

The microcontroller does **not replace the server**. Instead, it acts as a **hardware-backed session authority**, ensuring that attendance sessions are tied to a real physical classroom environment and cannot be started or manipulated remotely.

### **11.2 Role of the Arduino Uno**

The Arduino is responsible for:

* Acting as the **classroom identity anchor**
* Initiating and terminating attendance sessions via **physical buttons**
* Providing hardware-level confirmation that a class is active (**LEDs + buzzer**)
* Allowing course selection (buttons or rotary encoder)
* Optional: small **LCD/OLED** for displaying session status and student count

The Arduino explicitly does **not** handle:

* Student authentication logic
* Device-to-student binding
* Database storage
* Network communication (handled by the Pi)

### **11.3 Arduino ↔ Pi Communication**

Communication is via **USB Serial** (JSON protocol):

* Arduino sends session commands → Pi processes and responds
* Pi sends session status updates → Arduino displays via LEDs/LCD
* Baud rate: 9600 or 115200
* A Python `serial_bridge.py` script on the Pi handles the serial port

### **11.4 Session Authority Workflow**

1. Lecturer selects course code on the Arduino
2. Presses a physical button to **start session**
3. Arduino sends `{"action": "start_session", "course_code": "CSC301"}` via serial
4. Pi creates session, generates token, responds with `session_id`
5. Arduino lights **green LED**, optional beep
6. Lecturer presses button to **end session**
7. Arduino sends `{"action": "end_session"}`
8. Pi locks session → Arduino lights **red LED**

This ensures attendance cannot be started or manipulated remotely or through software alone.

### **11.5 Future MCU Upgrade Path**

When an **ESP32** becomes available, it can replace the Arduino Uno to add:

* Direct Wi-Fi communication (eliminating USB serial dependency)
* NFC/RFID reader integration
* Larger local buffer (SPIFFS/LittleFS)
* Bluetooth proximity verification

---

## **12\. Future Continuity & Extensions**

This system is intentionally modular to allow:

* **University database integration** (replace manual roster with API sync)
* Multi-classroom support (multiple Pi nodes syncing to same cloud)
* Biometric confirmation (fingerprint sensor on MCU)
* Bluetooth proximity verification
* Analytics & reporting dashboards
* University-wide deployment

The LAN-based system acts as the **foundation**, not the final form.

---

## **13\. Summary**

This proposed system translates basic networking principles into a structured, authenticated attendance platform. By combining **local networking** (Raspberry Pi hotspot), **device binding**, **session-based validation** (Arduino-controlled), and **cloud verification** (Supabase roster matching), it achieves a balance between practicality, security, and scalability.

The design prioritizes continuity — enabling future experts to extend the system without re-architecting its core.
