from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Length, EqualTo
from re import fullmatch, compile

def passwordValidate(form, field):
    """ 
    Validates the argument password to a regexp object, returns a Match object, or None
    """

    pwd_regexp = compile(r'^.*(?=.{8,})(?=.*[a-zA-Z])(?=.*?[A-Z])(?=.*\d)[a-zA-Z0-9!@£$%^&*()_+={}?:~\[\]]+$')

    if not fullmatch(pwd_regexp, field.data):
        raise ValidationError(message='Password must match the specific pattern')


def emailValidate(form, field):
    """ 
    Validates the email against a few criterias.
    Two main criteria:
        1. must contain at least one @ character, specifying the domain which the e-mail belongs to
        2. must contain at least one . character, which belongs also to the upper-mentioned domain
        3. Mustn't contain any whitespaces
    """

    if ' ' in field.data:
        raise ValidationError(message='Invalid e-mail address')

    if field.data.count('.') < 1:
        raise ValidationError(message='Invalid e-mail address')

    if field.data.count('@') < 1:
        raise ValidationError(message='Invalid e-mail address')


class LoginForm(FlaskForm):
    email = StringField(label='', validators=[DataRequired(), emailValidate])
    password = PasswordField(label='', validators=[DataRequired()])


class RegistrationForm(FlaskForm):
    email = StringField(label='', validators=[DataRequired(), emailValidate])
    name = StringField(label='', validators=[DataRequired(), Length(min=5)])
    password = PasswordField(label='', validators=[DataRequired(), Length(min=8, max=96), EqualTo('confirmPassword', message='Passwords must match'), passwordValidate])
    confirmPassword = PasswordField(label='')


class CommentForm(FlaskForm):
    comment = TextAreaField(label='Feel free to comment on this post', validators=[DataRequired(), Length(min=5)])


class ReplyForm(FlaskForm):
    reply = TextAreaField(label='', validators=[DataRequired(), Length(min=5)])


class PostForm(FlaskForm):
    title = StringField(label='What is the title of your post?', validators=[DataRequired(), Length(min=5, max=90)])
    post = TextAreaField(label='You should write your post in Markdown or plain text', validators=[DataRequired(), Length(min=15)])