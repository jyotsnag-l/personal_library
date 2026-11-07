# Personal Library Manager 📚

A clean, responsive web application built with **Python**, **FastAPI**, **SQLite**, **HTML5**, and **CSS3** for tracking books you own and books you want to read.

---

## Features

- **Book Cataloging**: Add books with title, author, genre, publication year, optional star rating (1–5), personal notes/reviews, and reading status.
- **Reading Status Management**: Seamlessly mark books as:
  - `Want to Read`
  - `Reading`
  - `Finished`
- **Dynamic Search & Multi-Criteria Filtering**: Filter books by author, genre, or reading status, or search across titles, authors, and notes.
- **Book Details & Notes**: View individual book cards, read full personal reflections, and edit or delete books anytime.
- **Analytics Dashboard**:
  - Total books owned
  - Books finished
  - Currently reading count
  - Reading queue progress breakdown
  - Average rating across all rated titles
- **Clean UI**: Modern, responsive interface styled with custom CSS (no heavy external CSS framework required).

---

## Dependencies & Prerequisites

- **Python 3.8+** (Python 3.10+ recommended)
- **FastAPI** & **Uvicorn**
- **Jinja2** & **python-multipart**

All dependencies are specified in `requirements.txt`. SQLite is included with Python's standard library.

---

## Installation & Setup

1. **Open PowerShell / Terminal** in the project directory:
   ```bash
   cd c:\Users\sreej\Desktop\personal_library
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **(Optional) Seed the database**:
   ```bash
   python database.py --seed
   ```

---

## Running the Application

You can start the server using either method:

### Method 1 (Direct Python command):
```bash
python app.py
```

### Method 2 (Uvicorn CLI):
```bash
uvicorn app:app --reload --port 9000
```

Once started, open your web browser and go to:
👉 **http://127.0.0.1:9000** (or **http://localhost:9000**)

---

## Database Management Helpers

The `database.py` file contains convenience CLI arguments:

- **Seed sample books**:
  ```bash
  python database.py --seed
  ```
- **Create a clean, empty database (no books)**:
  ```bash
  python database.py --empty
  ```

---

## Intentional Bugs for Debugging Practice

This application intentionally includes **two runtime bugs** left unfixed for debugging exercises:

1. **Bug 1: Dashboard crash with no rated books**: Calculating the average rating fails with `ZeroDivisionError: division by zero` when the library contains no rated books.
2. **Bug 2: Unhandled error on unsupported reading status**: Submitting an unlisted reading status raises an uncaught `ValueError` rather than displaying a user-friendly validation error message.

See [BUGS.md](file:///c:/Users/sreej/Desktop/personal_library/BUGS.md) for full reproduction steps and suggested fixes.

