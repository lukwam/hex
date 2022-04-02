# hex

Hex puzzles

## Schema

books:
* `id`: Examples include `ap`, `gdn`, `rha`, `rhg`, `sb`
* `title`: Title of the book
* `isbn_10`: ISBN-10 of the book
* `isbn_13`: ISBN-13 of the book
* `date`: Date the book was originally published
* `pages`: Number of pages in the book
* `amazon_url`: Amazon URL to purchase the book
* `cover_url`: URL of the cover of the book
* `images`: Dictionary of cached images associated with the book

publications:
* `id`: Examples include `wsj`, `alantic`, etc.
* `name`: Examples include `Wall Street Journal`, `The Alantic Puzzler`
* `url`: URL of the publication

puzzles:
* `title`: Title of the puzzle (not unique)
* `publication`: `id` from the `publications` collection
* `date`: Date the puzzle was published
* `issue`: Issue in which the puzle was published
* `web_url`: URL of puzzle web site (if available online)
* `puzzle_url`: URL of the puzzle file (PDF, etc.)
* `answer_url`: URL of the answer file (PDF, etc.)
* `images`: Dictionary of cached images associated with the puzzle

users:
* `id`: The unique ID of the user
* `email`: The email of the user
* `handle`: The user's handle for social features
* `books_owned`: List of books the user owns.
* `favorites`: List of puzles the user has favorited
* `puzzles_solved`: List of puzzles the user has solved.
* `is_admin`: True if the user is an admin
