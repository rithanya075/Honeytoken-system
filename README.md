# 🛡️ HAMS — Honeytoken Access Monitoring System

A **Security Operations Center (SOC) simulation platform** that leverages **database-level deception (honeytokens)** to detect unauthorized access, insider threats, and credential misuse in real time.

---

## Overview

HAMS is a full-stack cybersecurity application designed to demonstrate **active defense techniques** using **MySQL triggers and behavioral analytics**. The system embeds detection logic directly into the database layer, ensuring **tamper-resistant threat detection** even if the application layer is compromised.

---

##  Key Features

* 🪤 **Honeytoken-based intrusion detection** (decoy credentials & resources)
* ⚡ **Real-time alert generation using MySQL triggers**
* 📊 **Dynamic risk scoring engine** based on user behavior
* 🔍 **Brute-force detection** (failed login tracking & anomaly detection)
* 📈 **Interactive SOC dashboard** with live metrics (Chart.js)
* 🕵️ **Comprehensive audit logging** via stored procedures
* 🔐 **Session-based authentication system**

---

##  Architecture Highlights

* Detection logic implemented at the **database layer (MySQL triggers)**
* Risk score calculation automated using **event-driven updates**
* Modular Flask backend with separation of concerns (`app.py`, `db.py`, `config.py`)
* REST-driven frontend updates with periodic refresh

---

##  Tech Stack

* **Backend:** Python 3.13, Flask
* **Database:** MySQL 8.0
* **Frontend:** HTML, CSS, JavaScript
* **Visualization:** Chart.js

---

## Project Structure

```
honeytoken_system/
├── app.py
├── db.py
├── config.py
├── sql/
├── static/
└── templates/
```

---

##  Setup

```bash
pip install flask mysql-connector-python
python app.py
```

---

##  Default Credentials

| Username | Password |
| -------- | -------- |
| admin    | password |

---

##  Key Concepts Demonstrated

* Deception Technology (Honeytokens)
* Database Security via Triggers
* Behavioral Risk Scoring
* Insider Threat Detection
* Secure Web Application Design

---

##  Author

Rithanya — B.Tech Cybersecurity, SRM Institute of Science and Technology
