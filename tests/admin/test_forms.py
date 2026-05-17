"""Tests for services.admin.forms — WTForms validation."""

from __future__ import annotations

from services.admin.forms import APIKeyForm, BookForm, PublicationForm, PuzzleForm, UserForm


class TestPuzzleForm:
    """Tests for PuzzleForm — puzzle metadata editing."""

    def test_title_required(self, app):
        with app.test_request_context():
            form = PuzzleForm(data={"title": ""})
            assert not form.validate()

    def test_valid_form(self, app):
        with app.test_request_context():
            form = PuzzleForm(
                data={
                    "title": "Test Puzzle",
                    "author": "Test Author",
                    "date": "2023-08-26",
                },
            )
            assert form.validate()

    def test_optional_number(self, app):
        with app.test_request_context():
            form = PuzzleForm(data={"title": "Test", "number": ""})
            assert form.validate()
            assert form.number.data is None

    def test_has_expected_fields(self, app):
        with app.test_request_context():
            form = PuzzleForm()
            field_names = {f.name for f in form}
            assert "title" in field_names
            assert "publication" in field_names
            assert "date" in field_names
            assert "shape" in field_names


class TestBookForm:
    """Tests for BookForm."""

    def test_title_required(self, app):
        with app.test_request_context():
            form = BookForm(data={"title": ""})
            assert not form.validate()

    def test_valid_form(self, app):
        with app.test_request_context():
            form = BookForm(data={"title": "Test Book"})
            assert form.validate()


class TestPublicationForm:
    """Tests for PublicationForm."""

    def test_name_required(self, app):
        with app.test_request_context():
            form = PublicationForm(data={"name": ""})
            assert not form.validate()

    def test_valid_form(self, app):
        with app.test_request_context():
            form = PublicationForm(data={"name": "WSJ"})
            assert form.validate()


class TestUserForm:
    """Tests for UserForm."""

    def test_email_required(self, app):
        with app.test_request_context():
            form = UserForm(data={"email": ""})
            assert not form.validate()

    def test_has_expected_fields(self, app):
        with app.test_request_context():
            form = UserForm()
            field_names = {f.name for f in form}
            assert "email" in field_names
            assert "name" in field_names
            assert "admin" in field_names


class TestAPIKeyForm:
    """Tests for APIKeyForm."""

    def test_description_required(self, app):
        with app.test_request_context():
            form = APIKeyForm(data={"description": ""})
            assert not form.validate()

    def test_valid_form(self, app):
        with app.test_request_context():
            form = APIKeyForm(data={"description": "Test API key"})
            assert form.validate()
