# Personal Library Manager 📚

A clean, responsive web application built with **Python**, **Flask**, **SQLite**, **HTML5**, and **CSS3** for tracking books you own and books you want to read.

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

## Project Structure

```
├── app.py                 # Flask web application routes and controller logic
├── database.py            # SQLite schema, connection management, parameterized queries
├── requirements.txt       # Python package dependencies
├── README.md              # Project documentation and setup guide
├── BUGS.md                # Reproduction guide for the two intentional runtime bugs
├── library.db             # SQLite database file (created automatically on startup)
├── static/
│   └── style.css          # Modern CSS styling for cards, tables, badges, and layout
└── templates/
    ├── base.html          # Base template with navigation, alerts, and footer
    ├── dashboard.html     # Dashboard view with summary statistics and recent books
    ├── books.html         # Book browsing list with search and filter controls
    ├── book_detail.html   # Detailed book view and quick status changer
    ├── add_book.html      # Form to add a new book to the library
    └── edit_book.html     # Form to edit book details, ratings, and notes
```

---

## Dependencies & Prerequisites

- **Python 3.8+** (Python 3.10+ recommended)
- **Flask 3.0+**

All dependencies are specified in `requirements.txt`. SQLite is included with Python's standard library.

---

## Installation & Setup

1. **Clone or navigate into the project directory**:
   ```bash
   cd /path/to/personal-library
   ```

2. **(Optional) Create and activate a virtual environment**:
   - On Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - On macOS/Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database** *(automatic on first run, but can also be seeded manually)*:
   ```bash
   python database.py --seed
   ```

---

## Running the Application

Start the Flask development server:

```bash
python app.py
```

Then open your browser and navigate to:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

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

