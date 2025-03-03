import re
from flask import current_app
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, DecimalField, FloatField, HiddenField, MultipleFileField, SelectField, StringField, IntegerField, PasswordField, SubmitField, TextAreaField, ValidationError
from typing import Optional
from wtforms.validators import Optional, Email, EqualTo, DataRequired, NumberRange, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms_sqlalchemy.fields import QuerySelectField
from models import Country, Currency, db, Tenant, User
from datetime import datetime, date, timedelta

# from app_constants import ACCOUNTS, MAIN_CATEGORIES

# class SearchForm(FlaskForm):
#     location = StringField('Location', validators=[Optional()], render_kw={"placeholder": "Where to?"})
#     date_range = StringField('Dates', validators=[Optional()], render_kw={"placeholder": "Dates"})
#     submit = SubmitField('Search')

class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[Optional()])
    name = StringField('First Name', validators=[Optional()])
    lastname = StringField('Last Name', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email()])
    password = PasswordField('Password', validators=[Optional()])
    confirm_password = PasswordField('Confirm Password', validators=[Optional(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    login_field = StringField('Email or Username', validators=[Optional()])
    password = PasswordField('Password', validators=[Optional()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[Optional()])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Reset Password')

class ResendVerificationForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Resend Verification Email')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Send Password Reset Email')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[Optional()])
    new_password = PasswordField('New Password', validators=[Optional()])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Change Password')

