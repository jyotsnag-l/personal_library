import sqlite3
import os
import sys

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'library.db')
VALID_STATUSES = ["Want to Read", "Reading", "Finished"]

def get_db_connection():
    """Establish and return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(seed=True):
    """Initialize database schema and optionally populate sample data."""
    conn = get_db_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT NOT NULL,
                publication_year INTEGER,
                rating INTEGER,
                reading_status TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # If table is newly created and empty, optionally seed with sample books
        count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        if count == 0 and seed:
            seed_sample_books(conn)
    conn.close()

def seed_sample_books(conn=None):
    """Seeds the database with diverse sample books."""
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True

    sample_books = [
        ("The Great Gatsby", "F. Scott Fitzgerald", "Classic Fiction", 1925, 5, "Finished", "A poignant critique of the American Dream and the Jazz Age."),
        ("To Kill a Mockingbird", "Harper Lee", "Classic Fiction", 1960, 5, "Finished", "Masterpiece about justice, morality, and empathy in the Deep South."),
        ("1984", "George Orwell", "Dystopian", 1949, 4, "Reading", "Currently in Part 2. Hauntingly relevant examination of totalitarianism and surveillance."),
        ("Dune", "Frank Herbert", "Science Fiction", 1965, None, "Want to Read", "Recommended by friends; planned for next month."),
        ("Atomic Habits", "James Clear", "Self-Help", 2018, 4, "Finished", "Practical framework for continuous self-improvement and habit tracking.")
    ]

    with conn:
        conn.executemany("""
            INSERT INTO books (title, author, genre, publication_year, rating, reading_status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_books)

    if close_after:
        conn.close()

def get_all_books(search=None, author=None, genre=None, status=None):
    """Retrieve books with optional filtering by search query, author, genre, and status."""
    conn = get_db_connection()
    query = "SELECT * FROM books"
    conditions = []
    params = []

    if search:
        conditions.append("(title LIKE ? OR author LIKE ? OR notes LIKE ?)")
        search_param = f"%{search.strip()}%"
        params.extend([search_param, search_param, search_param])

    if author:
        conditions.append("author = ?")
        params.append(author.strip())

    if genre:
        conditions.append("genre = ?")
        params.append(genre.strip())

    if status:
        conditions.append("reading_status = ?")
        params.append(status.strip())

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"

    books = conn.execute(query, params).fetchall()
    conn.close()
    return books

def get_recent_books(limit=5):
    """Retrieve the most recently added books."""
    conn = get_db_connection()
    books = conn.execute(
        "SELECT * FROM books ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return books

def get_book_by_id(book_id):
    """Retrieve a single book by its ID."""
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return book

def add_book(title, author, genre, publication_year=None, rating=None, reading_status="Want to Read", notes=None):
    """Insert a new book into the database."""
    conn = get_db_connection()
    with conn:
        cursor = conn.execute("""
            INSERT INTO books (title, author, genre, publication_year, rating, reading_status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, author, genre, publication_year, rating, reading_status, notes))
        new_id = cursor.lastrowid
    conn.close()
    return new_id

def update_book(book_id, title, author, genre, publication_year=None, rating=None, reading_status="Want to Read", notes=None):
    """Update an existing book's details."""
    conn = get_db_connection()
    with conn:
        conn.execute("""
            UPDATE books
            SET title = ?, author = ?, genre = ?, publication_year = ?, rating = ?, reading_status = ?, notes = ?
            WHERE id = ?
        """, (title, author, genre, publication_year, rating, reading_status, notes, book_id))
    conn.close()

def update_book_status(book_id, reading_status, clear_rating=False):
    """Update only the reading status of a book, optionally clearing rating."""
    conn = get_db_connection()
    with conn:
        if clear_rating:
            conn.execute("UPDATE books SET reading_status = ?, rating = NULL WHERE id = ?", (reading_status, book_id))
        else:
            conn.execute("UPDATE books SET reading_status = ? WHERE id = ?", (reading_status, book_id))
    conn.close()

def delete_book(book_id):
    """Delete a book from the database by ID."""
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.close()

def get_distinct_authors():
    """Get sorted list of all unique authors."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT DISTINCT author FROM books 
        WHERE author IS NOT NULL AND TRIM(author) != '' 
        ORDER BY author COLLATE NOCASE ASC
    """).fetchall()
    conn.close()
    return [row['author'] for row in rows]

def get_distinct_genres():
    """Get sorted list of all unique genres."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT DISTINCT genre FROM books 
        WHERE genre IS NOT NULL AND TRIM(genre) != '' 
        ORDER BY genre COLLATE NOCASE ASC
    """).fetchall()
    conn.close()
    return [row['genre'] for row in rows]

def get_dashboard_stats():
    """
    Calculate summary statistics for the dashboard.
    
    INTENTIONAL BUG 1:
    When no books have ratings (or database is empty), ratings is empty [].
    Attempting to calculate avg_rating = sum(ratings) / len(ratings) raises
    ZeroDivisionError: division by zero, causing the dashboard to crash.
    """
    conn = get_db_connection()
    try:
        total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        finished_books = conn.execute("SELECT COUNT(*) FROM books WHERE reading_status = 'Finished'").fetchone()[0]
        currently_reading = conn.execute("SELECT COUNT(*) FROM books WHERE reading_status = 'Reading'").fetchone()[0]
        want_to_read = conn.execute("SELECT COUNT(*) FROM books WHERE reading_status = 'Want to Read'").fetchone()[0]

        # Fetch ratings for books that have been rated
        rated_rows = conn.execute("SELECT rating FROM books WHERE rating IS NOT NULL").fetchall()
        ratings = [row['rating'] for row in rated_rows]

        # Guard against division by zero when no books are rated
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

        return {
            'total_books': total_books,
            'finished_books': finished_books,
            'currently_reading': currently_reading,
            'want_to_read': want_to_read,
            'avg_rating': avg_rating,
            'rated_count': len(ratings)
        }
    finally:
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--seed':
        print("Initializing and seeding database...")
        init_db(seed=True)
        print("Database initialized with sample data.")
    elif len(sys.argv) > 1 and sys.argv[1] == '--empty':
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)
        print("Initializing empty database...")
        init_db(seed=False)
        print("Empty database initialized (no books).")
    else:
        init_db(seed=True)
        print("Database ready.")

