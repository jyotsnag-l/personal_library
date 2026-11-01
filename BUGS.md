# Known Bugs & Reproduction Guide

This document documents the two intentional runtime bugs present in the **Personal Library Manager** application, explaining how to run the application and reproduce both bugs directly through the web interface, along with their root causes and suggested fixes.

> **Note**: Do not fix these bugs if you are using this repository for debugging practice.

---

## Running the Application

1. **Activate your Python environment** and install requirements if not already done:
   ```bash
   pip install -r requirements.txt
   ```
2. **Start the Flask development server**:
   ```bash
   python app.py
   ```
3. **Open the web application** in your browser at:
   **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## Bug 1: Dashboard Crashes with `ZeroDivisionError` When No Books Have Ratings

### Description
When navigating to the dashboard (`/`), the application computes summary statistics, including the average rating across all rated books. If there are no rated books in the database (or if all books have their rating cleared/set to unrated), the server crashes with an unhandled `ZeroDivisionError`.

### Root Cause
In [database.py](file:///c:/Users/sreej/Desktop/personal_library/database.py#L186-L196):
```python
# Fetch ratings for books that have been rated
rated_rows = conn.execute("SELECT rating FROM books WHERE rating IS NOT NULL").fetchall()
ratings = [row['rating'] for row in rated_rows]

# Intentional Bug 1:
# When len(ratings) == 0, division by zero occurs
avg_rating = round(sum(ratings) / len(ratings), 1)
```
When no rated books exist in the database, `ratings` is an empty list `[]`. Its length is `0`, so dividing `sum(ratings) / len(ratings)` evaluates to `0 / 0`, raising:
```
ZeroDivisionError: division by zero
```

### Step-by-Step UI Reproduction Walkthrough

#### Step 1: Open the Books List
- Navigate to the Browse Books page:
  **URL:** [http://127.0.0.1:5000/books](http://127.0.0.1:5000/books) (or click **Browse All Books** or **Browse Books** in the navigation bar).

#### Step 2: Clear Ratings or Delete Rated Books via the UI
By default, the sample database contains 5 books (*The Great Gatsby*, *To Kill a Mockingbird*, *1984*, *Dune*, and *Atomic Habits*). Four of them have star ratings. You can remove all ratings using either of the following two UI methods:

- **Method A (Edit books to unrated):**
  1. For each book with stars (*The Great Gatsby*, *To Kill a Mockingbird*, *1984*, *Atomic Habits*):
     - Click the ✏️ (**Edit**) button in the **Actions** column on [http://127.0.0.1:5000/books](http://127.0.0.1:5000/books) (or navigate to `http://127.0.0.1:5000/books/<id>/edit`).
     - In the **Rating** dropdown field, select **"No rating (unrated)"** (the first option).
     - Notice that the **Reading Status** automatically updates to **"Want to Read"** (or change it to "Want to Read") so that completed statuses like "Finished" don't display alongside "Unrated", which looks inconsistent in the table.
     - Click the **Save Changes** button.
  2. Confirm on [http://127.0.0.1:5000/books](http://127.0.0.1:5000/books) that every book displays `Unrated` in the Rating column and `Want to Read` in the Status column.

- **Method B (Delete rated books):**
  1. In the books table on [http://127.0.0.1:5000/books](http://127.0.0.1:5000/books), click the 🗑️ (**Delete**) button for each rated book.
  2. Click **OK** on the browser confirmation prompt (`Are you sure you want to remove '...'?`).
  3. Leave only *Dune* (which is unrated) or delete all books.

#### Step 3: Trigger the Bug via the UI
- Click **Dashboard** in the top navigation bar (or navigate directly to [http://127.0.0.1:5000/](http://127.0.0.1:5000/)).

#### Observed Error
The web page fails to load and the browser displays Flask's debug error page (HTTP 500):
```text
ZeroDivisionError: division by zero
File "...\personal_library\database.py", line 195, in get_dashboard_stats
  avg_rating = round(sum(ratings) / len(ratings), 1)
```

### Suggested Fix
In [database.py](file:///c:/Users/sreej/Desktop/personal_library/database.py#L195), guard against an empty list before performing division:
```python
avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
```

---

## Bug 2: Submitting an Unsupported Reading Status Causes an Unhandled `ValueError`

### Description
When adding a book, editing a book, or updating a book's reading status, submitting a status value outside the allowed set (`"Want to Read"`, `"Reading"`, `"Finished"`) causes the application to raise an unhandled `ValueError` rather than showing a user-friendly validation message.

### Root Cause
In [app.py](file:///c:/Users/sreej/Desktop/personal_library/app.py#L120-L124), [app.py](file:///c:/Users/sreej/Desktop/personal_library/app.py#L193-L197), and [app.py](file:///c:/Users/sreej/Desktop/personal_library/app.py#L228-L232):
```python
VALID_STATUSES = ["Want to Read", "Reading", "Finished"]

# Intentional Bug 2:
if reading_status not in VALID_STATUSES:
    raise ValueError(
        f"Unsupported reading status: '{reading_status}'. Supported statuses are: {', '.join(VALID_STATUSES)}"
    )
```
Instead of catching the unsupported input, issuing a friendly flash error message (such as `flash("Invalid status", "error")`), and returning the user to the form, the code raises an unhandled `ValueError`, crashing the request with a 500 error page.

### Step-by-Step UI Reproduction Walkthrough

Because standard HTML `<select>` dropdowns and `<button>` elements render predefined values, submitting an unlisted value through the web interface is done by modifying an option value in the browser's Developer Tools (or using the browser console) before submitting the form.

#### Option A: On the "Add New Book" Page (`/books/add`)

1. **Open the Add Book Page**:
   - In the top navigation bar, click **+ Add Book** (or open [http://127.0.0.1:5000/books/add](http://127.0.0.1:5000/books/add)).
2. **Enter Book Data**:
   - **Book Title**: `Clean Code`
   - **Author**: `Robert C. Martin`
   - **Genre**: `Software Engineering`
   - *(Optional)* **Publication Year**: `2008`
3. **Inspect the Reading Status Dropdown**:
   - Right-click on the **Reading Status** dropdown box and click **Inspect** (or press `F12` / `Ctrl+Shift+I` to open Developer Tools).
4. **Modify the Option Value in the DOM**:
   - In the Elements inspector, find `<select id="reading_status" name="reading_status">`.
   - Expand the `<select>` tag to view its `<option>` children.
   - Double-click the `value` of any option (e.g. `<option value="Want to Read">Want to Read</option>`) and change it to an unsupported status, such as:
     ```html
     <option value="Abandoned">Abandoned</option>
     ```
     *(Alternatively, in the Developer Tools Console tab, run:*
     `document.getElementById('reading_status').options[0].value = 'Abandoned';`
     *)*
5. **Select the Option and Submit**:
   - Back in the browser page, ensure that modified option (`Abandoned`) is selected in the **Reading Status** dropdown.
   - Click the **Save Book to Library** button.
6. **Observed Error**:
   The application crashes with Flask's debug error page (HTTP 500):
   ```text
   ValueError: Unsupported reading status: 'Abandoned'. Supported statuses are: Want to Read, Reading, Finished
   File "...\personal_library\app.py", line 121, in add_book
     raise ValueError(
         f"Unsupported reading status: '{reading_status}'. Supported statuses are: {', '.join(VALID_STATUSES)}"
     )
   ```

---

#### Option B: On the "Edit Book" Page (`/books/<id>/edit`)

1. **Open the Edit Book Page**:
   - Go to [http://127.0.0.1:5000/books](http://127.0.0.1:5000/books).
   - Click ✏️ (**Edit**) on any existing book (e.g., [http://127.0.0.1:5000/books/1/edit](http://127.0.0.1:5000/books/1/edit)).
2. **Inspect & Modify Reading Status**:
   - Right-click the **Reading Status** dropdown &rarr; **Inspect**.
   - Change an `<option value="...">` to `<option value="On Hold">On Hold</option>`.
   - Select "On Hold" in the dropdown.
3. **Submit**:
   - Click the **Save Changes** button.
4. **Observed Error**:
   The page crashes with HTTP 500:
   ```text
   ValueError: Unsupported reading status: 'On Hold'. Supported statuses are: Want to Read, Reading, Finished
   File "...\personal_library\app.py", line 194, in edit_book
   ```

---

#### Option C: On the "Book Detail" Page (`/books/<id>`) via Quick Status Buttons

1. **Open Book Details**:
   - Click on any book title in the library list or navigate to [http://127.0.0.1:5000/books/1](http://127.0.0.1:5000/books/1).
2. **Inspect the Status Buttons**:
   - Under **Update Reading Status** in the right sidebar, right-click any of the status buttons (e.g., the `Want to Read` button) &rarr; **Inspect**.
   - In the Elements inspector, edit the button's `value` attribute from `value="Want to Read"` to `value="Dropped"`:
     ```html
     <button type="submit" name="reading_status" value="Dropped" class="...">
     ```
3. **Click the Button**:
   - Click the modified status button on the web page.
4. **Observed Error**:
   The page crashes with HTTP 500:
   ```text
   ValueError: Unsupported reading status: 'Dropped'. Supported statuses are: Want to Read, Reading, Finished
   File "...\personal_library\app.py", line 229, in update_status
   ```

---

### Suggested Fix
In [app.py](file:///c:/Users/sreej/Desktop/personal_library/app.py), replace the unhandled `raise ValueError(...)` with Flask flash messaging and re-rendering/redirecting:
```python
if reading_status not in VALID_STATUSES:
    flash(f"'{reading_status}' is not a valid status. Please select 'Want to Read', 'Reading', or 'Finished'.", "error")
    return render_template('add_book.html', form=request.form, statuses=VALID_STATUSES)
```
And apply the equivalent pattern in `edit_book` and `update_status`.
