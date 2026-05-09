# Hex App

The Flask web application for managing and browsing the Cox & Rathvon puzzle archive.

## Stack

- **Runtime:** App Engine Standard, Python 3.12
- **Framework:** Flask 3, gunicorn
- **Database:** Cloud Firestore
- **Storage:** GCS buckets (archive PDFs, images, thumbnails)
- **Auth:** Google Identity Services (One Tap), Flask signed sessions, CSRF protection

## Local Development

```bash
cd app
pip install -r requirements.txt
FLASK_SECRET_KEY=dev-secret-key flask run
```

## Deployment

Deployed automatically via Cloud Build on push to `main`.
The `cloudbuild.yaml` runs `gcloud app deploy`.

## Routes

### Public

| Route                | Description                   |
| -------------------- | ----------------------------- |
| `/`                  | Home page                     |
| `/books`             | List all books                |
| `/books/<id>`        | View a book                   |
| `/publications`      | List all publications         |
| `/publications/<id>` | View a publication            |
| `/puzzles`           | List all puzzles              |
| `/puzzles/<id>`      | View a puzzle                 |
| `/profile`           | User profile (solved puzzles) |

### Admin (`@admin_required`)

| Route                            | Description           |
| -------------------------------- | --------------------- |
| `/admin`                         | Admin dashboard       |
| `/admin/books/<id>/edit`         | Edit a book           |
| `/admin/publications/add`        | Add a publication     |
| `/admin/publications/<id>/edit`  | Edit a publication    |
| `/admin/puzzles/add`             | Add a puzzle          |
| `/admin/puzzles/<id>/edit`       | Edit a puzzle         |
| `/admin/puzzles/<id>/delete`     | Delete a puzzle       |
| `/archive`                       | Browse puzzle archive |
