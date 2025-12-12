# Golf Tracker

Golf Tracker is a small web app for tracking golf practice sessions.  
Each user gets their own bag of clubs, can log shots for each club, and see simple stats and a dispersion-style chart to understand their tendencies.

---

## Live Demo

Deployed on Render:  
https://golf-tracker-83b2.onrender.com

---

## Features

- **User accounts**
  - Register, log in, and log out.
  - Each user only sees their own clubs and shots.

- **Club management**
  - Add clubs with name, loft and notes (e.g. “7 iron – ZX7 / Modus 120X”).
  - Clubs are ordered logically in the bag (driver → woods → hybrids → irons → wedges → putter) using a custom ordering system that also looks at wedge lofts.

- **Shot logging**
  - Log shots with:
    - Date (defaults to “today”)
    - Club
    - Distance
    - Result / miss description (e.g. “pull left”, “block right”, “straight”)
    - Optional context/notes (range, simulator, course, etc.)
  - Quick entry form and a table of recent shots, with an optional date filter.

- **Per-club stats**
  - Average distance for each club.
  - Shot count per club.
  - Basic “miss pattern” buckets (left, center-left, center, center-right, right, other) calculated from the text result.

- **Dispersion-style chart**
  - Simple 2D “spray chart” built with HTML/CSS.
  - Each dot represents a shot:
    - Vertical position scaled by distance.
    - Horizontal lanes for left/center/right tendencies.
  - Different clubs get different colors and a legend.

---

## Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite (accessed via `cs50.SQL`)
- **Frontend:** HTML, Jinja templates, CSS
- **Auth & Security:**
  - Passwords hashed with Werkzeug’s `generate_password_hash`
  - Flask sessions secured with `SECRET_KEY`
- **Deployment:** Render (Gunicorn + Python web service)

---

## Data Model (simplified)

- **users**
  - `id` – primary key  
  - `username` – unique  
  - `hash` – password hash  

- **clubs**
  - `id` – primary key  
  - `user_id` – owner (FK → users.id)  
  - `name` – e.g. “7 iron”, “Driver”  
  - `loft` – numeric loft (optional)  
  - `notes` – free text description  
  - `bag_order` – integer used to sort clubs in a logical order  

- **shots**
  - `id` – primary key  
  - `club_id` – FK → clubs.id  
  - `date` – date of shot  
  - `distance` – numeric distance  
  - `result` – text description of miss/shape  
  - `context` – optional free text notes  

---

Originally developed as my final project for **Harvard CS50x 2025**.
