from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from flask_login import current_user 
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, HiddenField, FileField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from email_validator import validate_email, EmailNotValidError

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    email = StringField('Adresse email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('S\'inscrire')

    def validate_email_address(self, field):
        try:
            # Validate the email using email_validator
            v = validate_email(field.data)
            field.data = v["email"]  # normalized email address
        except EmailNotValidError as e:
            raise ValidationError(str(e))

class LoginForm(FlaskForm):
    email = StringField('Adresse email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class ArticleForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired()])
    content = TextAreaField('Contenu', validators=[DataRequired()])
    author_id = HiddenField('Auteur ID', validators=[DataRequired()])
    submit = SubmitField('Enregistrer')


class UpdateProfileForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    age = IntegerField('Age', validators=[Optional()])
    picture_filename = FileField('Ajouter une image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'svg'])])
    submit = SubmitField('Mettre à jour le profil')

class UpdatePostForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired()])
    content = TextAreaField('Contenu', validators=[DataRequired()])
    submit = SubmitField('Enregistrer')