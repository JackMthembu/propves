from datetime import datetime
from flask import Blueprint, render_template, redirect, session, url_for, flash, current_app
from models import User
from flask_login import login_user, logout_user, login_required, current_user, LoginManager
from forms import ChangePasswordForm, ForgotPasswordForm, LoginForm, ResendVerificationForm, ResetPasswordForm, SignUpForm
from flask_mail import Message
from extensions import mail
from models import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import BooleanField
from cachetools import TTLCache
from markupsafe import Markup

auth_routes = Blueprint('auth_routes', __name__)

login_manager = LoginManager()
session_cache = TTLCache(maxsize=100, ttl=300)

@login_manager.user_loader
def load_user(user_id):
    if user_id in session_cache:
        return session_cache[user_id]
    
    user = User.get_by_id(user_id)
    if user:
        session_cache[user_id] = user
    return user

@auth_routes.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    
    # Handle form submission
    if form.validate_on_submit():
        # Check if a user with the same email or username already exists
        user = User.query.filter(
            (User.email == form.email.data) | (User.username == form.username.data)
        ).first()
        
        if user:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('auth_routes.signup'))
        
        else:
            try:
                # Create a new user object
                new_user = User(
                    name=form.name.data,
                    lastname=form.lastname.data,
                    username=form.username.data,
                    email=form.email.data,
                    date_created=datetime.utcnow(),
                    password_hash=generate_password_hash(form.password.data)
                )
                
                # Add and commit the new user to the database
                db.session.add(new_user)
                db.session.commit()

                # Generate a verification token for the new user
                token = new_user.generate_verification_token(current_app.config['SECRET_KEY'])

                # Generate the verification URL for the email
                verification_url = url_for('auth_routes.verify_email', token=token, _external=True)

                # Set up email details
                subject = 'Welcome to PropVes - Please Verify Your Email'
                sender = current_app.config['MAIL_DEFAULT_SENDER']
                recipients = [new_user.email]
                
                # HTML and plain-text versions of the email
                body = f'''Hello {new_user.name},

Welcome to PropVes! We're excited to have you join our community.

To get started, please verify your email address by clicking the following link: {verification_url}

If you didn't create this account, please ignore this email.

Best regards,
The PropVes Team'''

                html = f'''
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #333;">Hello {new_user.name},</h2>
                        
                        <p>Welcome to PropVes! We're excited to have you join our community. 🎉</p>
                        
                        <p>To get started, please verify your email address:</p>
                        
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{verification_url}" 
                               style="background-color: #60D0AC; 
                                      color: white; 
                                      padding: 12px 25px; 
                                      text-decoration: none; 
                                      border-radius: 5px; 
                                      font-weight: bold;">
                                Verify Email
                            </a>
                        </p>
                        
                        <p style="color: #666; font-size: 0.9em;">
                            If the button doesn't work, copy and paste this link into your browser:<br>
                            <a href="{verification_url}" style="color: #60D0AC;">{verification_url}</a>
                        </p>
                        
                        <p style="color: #666; font-size: 0.9em;">
                            If you didn't create this account, please ignore this email.
                        </p>
                        
                        <p style="margin-top: 30px;">
                            Best regards,<br>
                            The PropVes Team
                        </p>
                    </div>
                '''

                # Send the verification email
                msg = Message(subject=subject, sender=sender, recipients=recipients, body=body, html=html)
                mail.send(msg)

                # Flash success message and redirect to login
                flash('Account created! Please check your email to verify your account. PLEASE NOTE: Your verification email may be in your spam folder.', 'success')
                return redirect(url_for('auth_routes.login'))
            
            except Exception as e:
                # Roll back if there's an error during user creation or email sending
                db.session.rollback()
                flash(f'Error sending verification email: {str(e)}', 'danger')
                return redirect(url_for('auth_routes.signup'))
    
    # Render the signup form
    return render_template('signup.html', form=form)


@auth_routes.route('/verify_email/<token>')
def verify_email(token):
    user = User.verify_verification_token(token, current_app.config['SECRET_KEY'])
    if user:
        user.verification = 'verified'
        db.session.commit()
        flash('Your email has been verified! You can now log in.', 'success')
        return redirect(url_for('auth_routes.login'))
    else:
        flash('The verification link is invalid or has expired.', 'danger')
        return redirect(url_for('auth_routes.signup'))
    
# =============================================================== resent for verification

@auth_routes.route('/resend_verification', methods=['GET', 'POST'])
def resend_verification():
    form = ResendVerificationForm()

    if form.validate_on_submit():
        # Find the user by email
        user = User.query.filter_by(email=form.email.data).first()

        if not user:
            flash('No account found with that email address.', 'danger')
            return redirect(url_for('auth_routes.resend_verification'))

        if user.verification == 'verified':
            flash('Your account is already verified.', 'info')
            return redirect(url_for('auth_routes.login'))

        # Generate new verification token
        token = user.generate_verification_token(current_app.config['SECRET_KEY'])
        verification_url = url_for('auth_routes.verify_email', token=token, _external=True)

        # Set up email details
        subject = 'Welcome to PropVes - Please Verify Your Email'
        sender = current_app.config['MAIL_DEFAULT_SENDER']
        recipients = [user.email]

        # HTML and plain-text versions of the email
        body = f'''Hello {user.name},

To get started, please verify your email address by clicking the following link: {verification_url}

If you didn't create this account, please ignore this email.

Best regards,
The PropVes Team'''

        html = f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">Hello {user.name},</h2>
                
                <p>To get started, please verify your email address:</p>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background-color: #60D0AC; 
                              color: white; 
                              padding: 12px 25px; 
                              text-decoration: none; 
                              border-radius: 5px; 
                              font-weight: bold;">
                        Verify Email
                    </a>
                </p>
                
                <p style="color: #666; font-size: 0.9em;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{verification_url}" style="color: #60D0AC;">{verification_url}</a>
                </p>
                
                <p style="color: #666; font-size: 0.9em;">
                    If you didn't create this account, please ignore this email.
                </p>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    The PropVes Team
                </p>
            </div>
        '''

        # Send the verification email
        msg = Message(subject=subject, sender=sender, recipients=recipients, body=body, html=html)
        mail.send(msg)

        flash('A new verification email has been sent. Please check your inbox.', 'success')
        return redirect(url_for('auth_routes.login'))

    return render_template('resend_verification.html', form=form)


@auth_routes.route('/resend_verification_token', methods=['GET', 'POST'])
def resend_verification_token():
    form = ResendVerificationForm()

    if form.validate_on_submit():
        # Find the user by email
        user = User.query.filter_by(email=form.email.data).first()

        if not user:
            flash('No account found with that email address.', 'danger')
            return redirect(url_for('auth_routes.resend_verification_token'))

        if user.verification == 'verified':
            flash('Your account is already verified.', 'info')
            return redirect(url_for('auth_routes.login'))

        # Generate new verification token
        token = user.generate_verification_token(current_app.config['SECRET_KEY'])
        verification_url = url_for('auth_routes.verify_email', token=token, _external=True)

        # Email details
        subject = 'Resend Email Verification Token'
        sender = current_app.config['MAIL_DEFAULT_SENDER']
        recipients = [user.email]
        body = f'Please verify your email by clicking the following link: {verification_url}'
        html = f'''
            <p>Please verify your email by clicking the link below:</p>
            <p><a href="{verification_url}" style="background-color:#60D0AC;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Verify Email</a></p>
            <p>If the button does not work, click the following link: <a href="{verification_url}">{verification_url}</a></p>
        '''

        # Send the email
        msg = Message(subject=subject, sender=sender, recipients=recipients, body=body, html=html)
        mail.send(msg)

        flash('A new verification email has been sent. Please check your inbox.', 'success')
        return redirect(url_for('auth_routes.login'))

    return render_template('resend_verification_token.html', form=form)


@auth_routes.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    print(f"Token received: {token}")
    
    user = User.verify_reset_token(token, current_app.config['SECRET_KEY'])
    if not user:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth_routes.forgot_password'))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        print(f"Form submitted with password: {form.password.data}")  # Debugging print
        # Update the user's password
        user.password_hash = generate_password_hash(form.password.data)
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('auth_routes.login'))

    return render_template('reset_password.html', form=form, token=token)  

 # ===========================================================================Email senfing function to rest the password
def send_reset_email(user):
    token = user.generate_reset_token()
    subject = 'Password Reset Request'
    sender = current_app.config['MAIL_DEFAULT_SENDER']
    recipients = [user.email]
    reset_url = url_for('auth_routes.reset_token', token=token, _external=True)
    body = f'''To reset your password, click the following link:
{reset_url}

If you did not make this request, simply ignore this email and no changes will be made.
'''
    html = f'''<p>To reset your password, click the following link:</p>
<p><a href="{reset_url}">Reset Password</a></p>
<p>If you did not make this request, simply ignore this email and no changes will be made.</p>
'''
    msg = Message(subject=subject, sender=sender, recipients=recipients, body=body, html=html)
    mail.send(msg)

# ================================================================ Logout

@auth_routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth_routes.login'))


@auth_routes.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if not user:
            flash('No account found with that email address.', 'danger')
            return redirect(url_for('auth_routes.forgot_password'))

        # Generate password reset token
        token = user.generate_reset_token(current_app.config['SECRET_KEY'])

        # Send reset email
        reset_url = url_for('auth_routes.reset_password', token=token, _external=True)
        subject = 'Password Reset Request'
        sender = current_app.config['MAIL_DEFAULT_SENDER']
        recipients = [user.email]
        body = f'Please reset your password by clicking the following link: {reset_url}'
        html = f'''
             <p>Dear User</p>
             <br>

            <p>Please reset your password by clicking the link below:</p>
            <p><a href="{reset_url}" style="background-color:#60D0AC;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Reset Password</a></p>
            <p>If the button does not work, click the following link: <a href="{reset_url}">{reset_url}</a></p>

            <strong>Please ignore this message, if you did not request a password request.</strong>
            <br>
            <p>Best Regards,</p>
            <strong>Propves,</strong>

        '''

        msg = Message(subject=subject, sender=sender, recipients=recipients, body=body, html=html)
        mail.send(msg)

        flash('A password reset email has been sent. Please check your inbox.', 'success')
        return redirect(url_for('auth_routes.login'))

    return render_template('forgot_password.html', form=form)


@auth_routes.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        # Verify the current password
        if not check_password_hash(current_user.password_hash, form.old_password.data):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth_routes.change_password'))

        # Update the user's password
        current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('auth_routes.profile'))

    return render_template('change_password.html', form=form)


@auth_routes.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_field = form.login_field.data
        password = form.password.data

        user = User.query.filter(
            (User.email == login_field) | (User.username == login_field)
        ).first()

        if user:
            if user.account_locked:
                flash('Your account is locked due to multiple failed login attempts. Please contact support.', 'danger')
                return redirect(url_for('auth_routes.login'))

            if user.verification != 'verified':
                flash(Markup('Your account is not verified. Please check your email for the verification link. If you did not receive it, you can <a href="' + url_for('auth_routes.resend_verification') + '">resend the verification email</a>. Please note that your verification email might be in your spam folder.'), 'warning')
                return redirect(url_for('auth_routes.login'))

            if user.check_password(password):
                login_user(user, remember=form.remember.data)
                session.permanent = True

                user.last_login = datetime.utcnow()
                user.failed_login_attempts = 0
                db.session.commit()
            
                flash('Logged in successfully!', 'success')
                return redirect(url_for('main.dashboard'))  
            else:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.account_locked = True
                    flash('Your account has been locked due to multiple failed login attempts.', 'danger')
                else:
                    flash('Invalid username or password', 'danger')
                db.session.commit()
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

