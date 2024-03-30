from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, TextAreaField
from wtforms.validators import InputRequired, Length, ValidationError, DataRequired
from flask_bcrypt import Bcrypt
from datetime import datetime
import flask_login
from sqlalchemy.orm import backref
from dateutil.relativedelta import relativedelta
from datetime import date
import os

app = Flask(__name__)


with app.app_context():
    app.config['UPLOAD_FOLDER'] = 'static/profile-pics'  # Folder to store uploaded images
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SECRET_KEY'] = 'thisisasecretkey'
    db = SQLAlchemy(app)
    bcrypt = Bcrypt(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Follow(db.Model):
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now())

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(1000), nullable=False)
    receiver = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now())

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(80), nullable=True)
    birthday = db.Column(db.Date, nullable=False)
    profile_pic = db.Column(db.LargeBinary, default='/static/profile-pics/default.jpg')
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                              foreign_keys=[Follow.followed_id],
                              backref=db.backref('followed', lazy='joined'),
                              lazy='dynamic',
                              cascade='all, delete-orphan')
    postsender = db.relationship("Post", backref=backref("postsender", uselist=False), foreign_keys=[Post.sender], lazy=True)


    


class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    first_name = StringField(validators=[
                           InputRequired(), Length(min=2, max=20)], render_kw={"placeholder": "First Name"})
    birthday = DateField('Birthday', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                'That username already exists. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')

class PostForm(FlaskForm):
    body = TextAreaField(validators=[
                           InputRequired(), Length(min=3, max=2000)], render_kw={"placeholder": "Wish them a Happy Birthday!!"})
    submit = SubmitField('Send')


@app.route('/')
def home():
    todaybday = User.query.filter_by(birthday=date.today()).all()
    today = date.today()
    three_months_later = today + relativedelta(months=3)
    upcoming = User.query.filter(User.birthday >= date.today(), User.birthday <= three_months_later).all()
    return render_template('home.html', today=todaybday, upcoming=upcoming)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('profile', username=user.username))
    return render_template('login.html', form=form)


@app.route('/<username>', methods=['GET', 'POST'])
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    form = PostForm()
    print(flask_login.current_user.id)
    wishes = Post.query.filter_by(receiver=user.id)

    if form.validate_on_submit():
        newsender = flask_login.current_user
        new_post = Post(sender=newsender.id, receiver=user.id, body=form.body.data, timestamp=datetime.now())
        db.session.add(new_post)
        db.session.commit()
        print(newsender.id)
        print(new_post)
        print(form.body.data)
        return redirect(url_for('profile', username=user.username))

    if request.method == 'POST':
        # Handle file upload
        if 'profile_pic' in request.files:
            profile_pic = request.files['profile_pic']
            if profile_pic.filename:
                filename = secure_filename(profile_pic.filename)
                profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # Save 'filename' to your database for the user's profile

    return render_template('profile.html', user=user, form=form, wishes=wishes)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        print(form.birthday.data)
        new_user = User(username=form.username.data, password=hashed_password, birthday=form.birthday.data, first_name=form.first_name.data)
        db.session.add(new_user)
        db.session.commit()
        print('success')
        return redirect(url_for('login'))
    

    return render_template('register.html', form=form)



if __name__ == "__main__":
    app.run(debug=True)