"""Hex Admin — WTForms for model editing."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField
from wtforms.validators import DataRequired, Email


class UserForm(FlaskForm):
    """Form for creating/editing a user."""

    email = StringField("Email", validators=[DataRequired(), Email()])
    name = StringField("Name")
    first_name = StringField("First Name")
    last_name = StringField("Last Name")
    admin = BooleanField("Admin")
