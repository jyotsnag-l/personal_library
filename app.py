import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
import database
from recovery_sdk.integrations.fastapi import RecoveryMiddleware

app = Flask(__name__)
app.secret_key = 'personal-library-secret-key-change-in-production'

VALID_STATUSES = ["Want to Read", "Reading", "Finished"]

app.add_middleware(
    RecoveryMiddleware,
    project_id="proj_04102d07",        # your project ID from the platform
    environment="production",
    api_url="http://127.0.0.1:8000" # your Overmend API
)


@app.before_request
def ensure_db():
    """Ensure database exists and is initialized."""
    # Runs init_db with seed=True if DB doesn't exist yet
    if not os.path.exists(database.DB_NAME):
        database.init_db(seed=True)

@app.route('/')
def dashboard():
    """
    Dashboard view showing library statistics and recent books.
    
    INTENTIONAL BUG 1:
    If there are no rated books in the database, `get_dashboard_stats()`
    raises ZeroDivisionError when trying to compute the average rating.
    """
    stats = database.get_dashboard_stats()
    recent_books = database.get_recent_books(limit=5)
    return render_template('dashboard.html', stats=stats, recent_books=recent_books)

@app.route('/books')
def book_list():
    """
    Display list of books with search and filtering by author, genre, or status.
    """
    search_query = request.args.get('q', '').strip()
    selected_author = request.args.get('author', '').strip()
    selected_genre = request.args.get('genre', '').strip()
    selected_status = request.args.get('status', '').strip()

    books = database.get_all_books(
        search=search_query if search_query else None,
        author=selected_author if selected_author else None,
        genre=selected_genre if selected_genre else None,
        status=selected_status if selected_status else None
    )

    authors = database.get_distinct_authors()
    genres = database.get_distinct_genres()

    return render_template(
        'books.html',
        books=books,
        authors=authors,
        genres=genres,
        statuses=VALID_STATUSES,
        search_query=search_query,
        selected_author=selected_author,
        selected_genre=selected_genre,
        selected_status=selected_status
    )

@app.route('/books/<int:book_id>')
def book_detail(book_id):
    """View details of a specific book."""
    book = database.get_book_by_id(book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for('book_list'))
    return render_template('book_detail.html', book=book, statuses=VALID_STATUSES)

@app.route('/books/add', methods=['GET', 'POST'])
def add_book():
    """Add a new book to the library."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        genre = request.form.get('genre', '').strip()
        pub_year_raw = request.form.get('publication_year', '').strip()
        rating_raw = request.form.get('rating', '').strip()
        reading_status = request.form.get('reading_status', '').strip()
        notes = request.form.get('notes', '').strip()

        # Friendly form validation for required fields
        if not title:
            flash("Book title is required.", "error")
            return render_template('add_book.html', form=request.form, statuses=VALID_STATUSES)
        if not author:
            flash("Author name is required.", "error")
            return render_template('add_book.html', form=request.form, statuses=VALID_STATUSES)
        if not genre:
            flash("Genre is required.", "error")
            return render_template('add_book.html', form=request.form, statuses=VALID_STATUSES)

        # Parse publication year
        pub_year = None
        if pub_year_raw:
            try:
                pub_year = int(pub_year_raw)
            except ValueError:
                flash("Publication year must be a valid number.", "error")
                return render_template('add_book.html', form=request.form, statuses=VALID_STATUSES)

        # Parse rating
        rating = None
        if rating_raw:
            try:
                rating = int(rating_raw)
                if not (1 <= rating <= 5):
                    flash("Rating must be between 1 and 5.", "error")
                    return render_template('add_book.html', form=request.form, statuses=VALID_STATUSES)
            except ValueError:
                flash("Rating must be an integer between 1 and 5.", "error")
                return render_template('add_book.html', form=request.form, statuses=VALID_STATUSES)

        # -------------------------------------------------------------
        # INTENTIONAL BUG 2:
        # Submitting an unsupported reading status causes an unhandled error (ValueError)
        # instead of displaying a friendly validation message to the user.
        # -------------------------------------------------------------
        if reading_status not in VALID_STATUSES:
            raise ValueError(
                f"Unsupported reading status: '{reading_status}'. Supported statuses are: {', '.join(VALID_STATUSES)}"
            )

        # Ensure status and rating stay realistic across every condition:
        if rating is not None and rating >= 1:
            if reading_status in ["Want to Read", "Reading"]:
                reading_status = "Finished"
        elif reading_status == "Finished":
            reading_status = "Want to Read"

        if reading_status in ["Want to Read", "Reading"]:
            rating = None

        new_id = database.add_book(
            title=title,
            author=author,
            genre=genre,
            publication_year=pub_year,
            rating=rating,
            reading_status=reading_status,
            notes=notes if notes else None
        )
        flash(f"Book '{title}' added successfully!", "success")
        return redirect(url_for('book_detail', book_id=new_id))

    return render_template('add_book.html', form={}, statuses=VALID_STATUSES)

@app.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
def edit_book(book_id):
    """Edit an existing book's details, rating, status, or notes."""
    book = database.get_book_by_id(book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for('book_list'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        genre = request.form.get('genre', '').strip()
        pub_year_raw = request.form.get('publication_year', '').strip()
        rating_raw = request.form.get('rating', '').strip()
        reading_status = request.form.get('reading_status', '').strip()
        notes = request.form.get('notes', '').strip()

        # Friendly form validation for required fields
        if not title:
            flash("Book title cannot be empty.", "error")
            return render_template('edit_book.html', book=book, statuses=VALID_STATUSES)
        if not author:
            flash("Author name cannot be empty.", "error")
            return render_template('edit_book.html', book=book, statuses=VALID_STATUSES)
        if not genre:
            flash("Genre cannot be empty.", "error")
            return render_template('edit_book.html', book=book, statuses=VALID_STATUSES)

        # Parse publication year
        pub_year = None
        if pub_year_raw:
            try:
                pub_year = int(pub_year_raw)
            except ValueError:
                flash("Publication year must be a valid number.", "error")
                return render_template('edit_book.html', book=book, statuses=VALID_STATUSES)

        # Parse rating
        rating = None
        if rating_raw:
            try:
                rating = int(rating_raw)
                if not (1 <= rating <= 5):
                    flash("Rating must be between 1 and 5.", "error")
                    return render_template('edit_book.html', book=book, statuses=VALID_STATUSES)
            except ValueError:
                flash("Rating must be an integer between 1 and 5.", "error")
                return render_template('edit_book.html', book=book, statuses=VALID_STATUSES)

        # -------------------------------------------------------------
        # INTENTIONAL BUG 2:
        # Updating a book to an unsupported reading status causes an unhandled error (ValueError)
        # instead of displaying a friendly validation message.
        # -------------------------------------------------------------
        if reading_status not in VALID_STATUSES:
            raise ValueError(
                f"Unsupported reading status: '{reading_status}'. Supported statuses are: {', '.join(VALID_STATUSES)}"
            )

        # Ensure status and rating stay realistic across every condition:
        if rating is not None and rating >= 1:
            if reading_status in ["Want to Read", "Reading"]:
                reading_status = "Finished"
        elif reading_status == "Finished":
            reading_status = "Want to Read"

        if reading_status in ["Want to Read", "Reading"]:
            rating = None

        database.update_book(
            book_id=book_id,
            title=title,
            author=author,
            genre=genre,
            publication_year=pub_year,
            rating=rating,
            reading_status=reading_status,
            notes=notes if notes else None
        )
        flash("Book updated successfully!", "success")
        return redirect(url_for('book_detail', book_id=book_id))

    return render_template('edit_book.html', book=book, statuses=VALID_STATUSES)

@app.route('/books/<int:book_id>/status', methods=['POST'])
def update_status(book_id):
    """Quickly update the reading status of a book."""
    book = database.get_book_by_id(book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for('book_list'))

    new_status = request.form.get('reading_status', '').strip()

    # -------------------------------------------------------------
    # INTENTIONAL BUG 2:
    # Updating a book to an unsupported reading status causes an unhandled error (ValueError)
    # instead of displaying a friendly validation message.
    # -------------------------------------------------------------
    if new_status not in VALID_STATUSES:
        raise ValueError(
            f"Unsupported reading status: '{new_status}'. Supported statuses are: {', '.join(VALID_STATUSES)}"
        )

    clear_rating = (new_status in ["Want to Read", "Reading"])
    database.update_book_status(book_id, new_status, clear_rating=clear_rating)
    flash(f"Status for '{book['title']}' updated to '{new_status}'.", "success")
    return redirect(request.referrer or url_for('book_detail', book_id=book_id))

@app.route('/books/<int:book_id>/delete', methods=['POST'])
def delete_book(book_id):
    """Delete a book from the library."""
    book = database.get_book_by_id(book_id)
    if not book:
        flash("Book not found.", "error")
    else:
        database.delete_book(book_id)
        flash(f"Book '{book['title']}' has been removed from your library.", "info")
    return redirect(url_for('book_list'))

if __name__ == '__main__':
    # Initialize DB if needed
    database.init_db(seed=True)
    print("Personal Library Manager running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)

