import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import jinja2
from recovery_sdk.integrations.fastapi import RecoveryMiddleware
import database

# Directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

VALID_STATUSES = ["Want to Read", "Reading", "Finished"]

# Lifespan event to ensure DB is initialized on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database exists and is initialized."""
    if not os.path.exists(database.DB_NAME):
        database.init_db(seed=True)
    yield

app = FastAPI(
    title="Personal Library Manager",
    description="Track books you own and books you want to read",
    lifespan=lifespan
)

# Recovery SDK middleware for error tracking and recovery
app.add_middleware(
    RecoveryMiddleware,
    project_id="proj_04102d07",        # your project ID from the platform
    environment="production",
    api_url="http://127.0.0.1:8000"     # your Overmend API
)

# Enable session support for flash messages and state
app.add_middleware(
    SessionMiddleware,
    secret_key="personal-library-secret-key-change-in-production"
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates configuration
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Flask-compatibility extensions for Starlette Request
def _get_request_endpoint(self):
    endpoint = self.scope.get("endpoint")
    if endpoint:
        return getattr(endpoint, "__name__", "")
    return ""

def _get_request_referrer(self):
    return self.headers.get("referer", "")

Request.endpoint = property(_get_request_endpoint)
Request.referrer = property(_get_request_referrer)

# Custom url_for helper supporting both path and filename (for static files)
orig_url_for = Request.url_for

def custom_url_for(self, name: str, **path_params):
    if name == "static" and "filename" in path_params and "path" not in path_params:
        path_params["path"] = path_params.pop("filename")
    return orig_url_for(self, name, **path_params)

Request.url_for = custom_url_for

# Flash message utilities compatible with Jinja2 templates
def flash(request: Request, message: str, category: str = "info"):
    """Store a flash message in the session."""
    if "_flashes" not in request.session:
        request.session["_flashes"] = []
    request.session["_flashes"].append((category, message))

@jinja2.pass_context
def get_flashed_messages(context, with_categories: bool = False):
    """Retrieve and clear flash messages from session."""
    request = context.get("request")
    if not request or "_flashes" not in request.session:
        return []
    flashes = request.session.pop("_flashes", [])
    if not with_categories:
        return [msg for cat, msg in flashes]
    return flashes

templates.env.globals["get_flashed_messages"] = get_flashed_messages


# --- Routes ---

@app.get("/", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request):
    """
    Dashboard view showing library statistics and recent books.
    
    INTENTIONAL BUG 1:
    If there are no rated books in the database, `get_dashboard_stats()`
    raises ZeroDivisionError when trying to compute the average rating.
    """
    stats = database.get_dashboard_stats()
    recent_books = database.get_recent_books(limit=5)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"stats": stats, "recent_books": recent_books}
    )

@app.get("/books", response_class=HTMLResponse, name="book_list")
async def book_list(
    request: Request,
    q: Optional[str] = "",
    author: Optional[str] = "",
    genre: Optional[str] = "",
    status: Optional[str] = ""
):
    """
    Display list of books with search and filtering by author, genre, or status.
    """
    search_query = (q or "").strip()
    selected_author = (author or "").strip()
    selected_genre = (genre or "").strip()
    selected_status = (status or "").strip()

    books = database.get_all_books(
        search=search_query if search_query else None,
        author=selected_author if selected_author else None,
        genre=selected_genre if selected_genre else None,
        status=selected_status if selected_status else None
    )

    authors = database.get_distinct_authors()
    genres = database.get_distinct_genres()

    return templates.TemplateResponse(
        request=request,
        name="books.html",
        context={
            "books": books,
            "authors": authors,
            "genres": genres,
            "statuses": VALID_STATUSES,
            "search_query": search_query,
            "selected_author": selected_author,
            "selected_genre": selected_genre,
            "selected_status": selected_status
        }
    )

@app.get("/books/{book_id}", response_class=HTMLResponse, name="book_detail")
async def book_detail(request: Request, book_id: int):
    """View details of a specific book."""
    book = database.get_book_by_id(book_id)
    if not book:
        flash(request, "Book not found.", "error")
        return RedirectResponse(url=str(request.url_for("book_list")), status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="book_detail.html",
        context={"book": book, "statuses": VALID_STATUSES}
    )

@app.get("/books/add", response_class=HTMLResponse, name="add_book")
async def add_book_form(request: Request):
    """Show form to add a new book."""
    return templates.TemplateResponse(
        request=request,
        name="add_book.html",
        context={"form": {}, "statuses": VALID_STATUSES}
    )

@app.post("/books/add", response_class=HTMLResponse)
async def add_book(request: Request):
    """Add a new book to the library."""
    form_data = await request.form()
    title = str(form_data.get("title", "")).strip()
    author = str(form_data.get("author", "")).strip()
    genre = str(form_data.get("genre", "")).strip()
    pub_year_raw = str(form_data.get("publication_year", "")).strip()
    rating_raw = str(form_data.get("rating", "")).strip()
    reading_status = str(form_data.get("reading_status", "")).strip()
    notes = str(form_data.get("notes", "")).strip()

    # Friendly form validation for required fields
    if not title:
        flash(request, "Book title is required.", "error")
        return templates.TemplateResponse(
            request=request,
            name="add_book.html",
            context={"form": dict(form_data), "statuses": VALID_STATUSES}
        )
    if not author:
        flash(request, "Author name is required.", "error")
        return templates.TemplateResponse(
            request=request,
            name="add_book.html",
            context={"form": dict(form_data), "statuses": VALID_STATUSES}
        )
    if not genre:
        flash(request, "Genre is required.", "error")
        return templates.TemplateResponse(
            request=request,
            name="add_book.html",
            context={"form": dict(form_data), "statuses": VALID_STATUSES}
        )

    # Parse publication year
    pub_year = None
    if pub_year_raw:
        try:
            pub_year = int(pub_year_raw)
        except ValueError:
            flash(request, "Publication year must be a valid number.", "error")
            return templates.TemplateResponse(
                request=request,
                name="add_book.html",
                context={"form": dict(form_data), "statuses": VALID_STATUSES}
            )

    # Parse rating
    rating = None
    if rating_raw:
        try:
            rating = int(rating_raw)
            if not (1 <= rating <= 5):
                flash(request, "Rating must be between 1 and 5.", "error")
                return templates.TemplateResponse(
                    request=request,
                    name="add_book.html",
                    context={"form": dict(form_data), "statuses": VALID_STATUSES}
                )
        except ValueError:
            flash(request, "Rating must be an integer between 1 and 5.", "error")
            return templates.TemplateResponse(
                request=request,
                name="add_book.html",
                context={"form": dict(form_data), "statuses": VALID_STATUSES}
            )

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
    flash(request, f"Book '{title}' added successfully!", "success")
    return RedirectResponse(url=str(request.url_for("book_detail", book_id=new_id)), status_code=303)

@app.get("/books/{book_id}/edit", response_class=HTMLResponse, name="edit_book")
async def edit_book_form(request: Request, book_id: int):
    """Show form to edit an existing book."""
    book = database.get_book_by_id(book_id)
    if not book:
        flash(request, "Book not found.", "error")
        return RedirectResponse(url=str(request.url_for("book_list")), status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="edit_book.html",
        context={"book": book, "statuses": VALID_STATUSES}
    )

@app.post("/books/{book_id}/edit", response_class=HTMLResponse)
async def edit_book(request: Request, book_id: int):
    """Edit an existing book's details, rating, status, or notes."""
    book = database.get_book_by_id(book_id)
    if not book:
        flash(request, "Book not found.", "error")
        return RedirectResponse(url=str(request.url_for("book_list")), status_code=303)

    form_data = await request.form()
    title = str(form_data.get("title", "")).strip()
    author = str(form_data.get("author", "")).strip()
    genre = str(form_data.get("genre", "")).strip()
    pub_year_raw = str(form_data.get("publication_year", "")).strip()
    rating_raw = str(form_data.get("rating", "")).strip()
    reading_status = str(form_data.get("reading_status", "")).strip()
    notes = str(form_data.get("notes", "")).strip()

    # Friendly form validation for required fields
    if not title:
        flash(request, "Book title cannot be empty.", "error")
        return templates.TemplateResponse(
            request=request,
            name="edit_book.html",
            context={"book": book, "statuses": VALID_STATUSES}
        )
    if not author:
        flash(request, "Author name cannot be empty.", "error")
        return templates.TemplateResponse(
            request=request,
            name="edit_book.html",
            context={"book": book, "statuses": VALID_STATUSES}
        )
    if not genre:
        flash(request, "Genre cannot be empty.", "error")
        return templates.TemplateResponse(
            request=request,
            name="edit_book.html",
            context={"book": book, "statuses": VALID_STATUSES}
        )

    # Parse publication year
    pub_year = None
    if pub_year_raw:
        try:
            pub_year = int(pub_year_raw)
        except ValueError:
            flash(request, "Publication year must be a valid number.", "error")
            return templates.TemplateResponse(
                request=request,
                name="edit_book.html",
                context={"book": book, "statuses": VALID_STATUSES}
            )

    # Parse rating
    rating = None
    if rating_raw:
        try:
            rating = int(rating_raw)
            if not (1 <= rating <= 5):
                flash(request, "Rating must be between 1 and 5.", "error")
                return templates.TemplateResponse(
                    request=request,
                    name="edit_book.html",
                    context={"book": book, "statuses": VALID_STATUSES}
                )
        except ValueError:
            flash(request, "Rating must be an integer between 1 and 5.", "error")
            return templates.TemplateResponse(
                request=request,
                name="edit_book.html",
                context={"book": book, "statuses": VALID_STATUSES}
            )

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
    flash(request, "Book updated successfully!", "success")
    return RedirectResponse(url=str(request.url_for("book_detail", book_id=book_id)), status_code=303)

@app.post("/books/{book_id}/status", name="update_status")
async def update_status(request: Request, book_id: int):
    """Quickly update the reading status of a book."""
    book = database.get_book_by_id(book_id)
    if not book:
        flash(request, "Book not found.", "error")
        return RedirectResponse(url=str(request.url_for("book_list")), status_code=303)

    form_data = await request.form()
    new_status = str(form_data.get("reading_status", "")).strip()

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
    flash(request, f"Status for '{book['title']}' updated to '{new_status}'.", "success")

    redirect_target = request.referrer or str(request.url_for("book_detail", book_id=book_id))
    return RedirectResponse(url=redirect_target, status_code=303)

@app.post("/books/{book_id}/delete", name="delete_book")
async def delete_book(request: Request, book_id: int):
    """Delete a book from the library."""
    book = database.get_book_by_id(book_id)
    if not book:
        flash(request, "Book not found.", "error")
    else:
        database.delete_book(book_id)
        flash(request, f"Book '{book['title']}' has been removed from your library.", "info")
    return RedirectResponse(url=str(request.url_for("book_list")), status_code=303)

if __name__ == "__main__":
    import uvicorn
    # Initialize DB if needed
    database.init_db(seed=True)
    print("Personal Library Manager running at http://127.0.0.1:8000")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
