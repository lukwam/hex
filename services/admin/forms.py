"""Hex Admin — WTForms for model editing."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Optional


class UserForm(FlaskForm):
    """Form for creating/editing a user."""

    email = StringField("Email", validators=[DataRequired(), Email()])
    name = StringField("Name")
    first_name = StringField("First Name")
    last_name = StringField("Last Name")
    admin = BooleanField("Admin")


class BookForm(FlaskForm):
    """Form for creating/editing a book."""

    title = StringField("Title", validators=[DataRequired()])
    code = StringField("Code")
    date = StringField("Date")
    publisher = StringField("Publisher")
    source = StringField("Source")
    isbn_10 = StringField("ISBN-10")
    isbn_13 = StringField("ISBN-13")
    amazon_link = StringField("Amazon Link")
    notes = StringField("Notes")


class PublicationForm(FlaskForm):
    """Form for creating/editing a publication."""

    name = StringField("Name", validators=[DataRequired()])
    code = StringField("Code")
    url = StringField("URL")


class PuzzleForm(FlaskForm):
    """Form for creating/editing puzzle metadata.

    Grid and clue editing is a separate, more complex feature.
    """

    title = StringField("Title", validators=[DataRequired()])
    author = StringField("Author")
    publication = SelectField("Publication", choices=[], validate_choice=False)
    number = IntegerField("Number", validators=[Optional()])
    date = StringField("Date")
    issue = StringField("Issue")
    editor = StringField("Editor")
    shape = StringField("Shape")
    instructions = TextAreaField("Instructions / Introduction")
    solution = TextAreaField("Solution Text")


class APIKeyForm(FlaskForm):
    """Form for creating an API key."""

    description = StringField("Description", validators=[DataRequired()])
