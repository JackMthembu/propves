from ast import main
import os
from flask import Blueprint, abort, current_app, flash, redirect, render_template, url_for, request
from flask_login import current_user, login_required
from sqlalchemy import func
# from investment_analyses import oer_analysis
from models import MaintainanceReport, Property, Listing, RentalAgreement, Transaction, User, db, Message, Owner, BankingDetails
from datetime import datetime, timedelta, date
from sqlalchemy.orm import joinedload

main = Blueprint('main', __name__)

@main.route('/')
def dashbard():
    return render_template('dashboard/dashbard.html')