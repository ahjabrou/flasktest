from flask import Flask, render_template, redirect, url_for, flash, session, request, send_from_directory
from flask_login import login_user, current_user, logout_user, login_required, LoginManager, UserMixin
from forms import RegistrationForm, LoginForm, ArticleForm, UpdateProfileForm, UpdatePostForm
from werkzeug.utils import secure_filename
from flask_pymongo import PyMongo
from datetime import datetime 
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os
from bson import ObjectId
from flask_session import Session
from decouple import config

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = config('MONGO_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = 'static/author_profile_pic'  # Mettez à jour avec le chemin de votre dossier de téléchargement
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

Session(app)
mongo = PyMongo(app)
# mongodb_client=PyMongo(app)
# mongo=mongodb_client
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

# Indiquez la vue pour la connexion (utilisé par Flask-Login pour gérer les connexions)
login_manager.login_view = 'login'  # 'login' doit être remplacé par le nom de votre route de connexion ici c'est login

@login_manager.user_loader
def load_user(user_id):
    # Load the user from your database and return an instance of the User class
    return User.load_user(user_id)

class User(UserMixin):
    def __init__(self, user_id, username, email, password, age=None, picture_filename=None):
        self.id = str(user_id)
        self.username = username
        self.email = email
        self.password = password
        self.age = age
        self.picture_filename = picture_filename

    @staticmethod
    def load_user(user_id):
        author = mongo.db.authors.find_one({'_id': ObjectId(user_id)})
        if author:
            return User(author['_id'], author['username'], author['email'], author['password'], author.get('age'), author.get('picture_filename'))
        return None

    @staticmethod
    def find_by_email(email):
        author = mongo.db.authors.find_one({'email': email})
        if author:
            return User(author['_id'], author['username'], author['email'], author['password'], author.get('age'), author.get('picture_filename'))
        return None

    @staticmethod
    def create_user(username, email, password):
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        author_id = mongo.db.authors.insert_one({'username': username, 'email': email, 'password': hashed_password}).inserted_id
        return User(author_id, username, email, hashed_password)

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

# pour l'image du formulaire
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#pour afficher l'image de profil

@app.route('/author_profile_pic/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#pour afficher une simple image
@app.route('/other_pic/<path:filename>')
def serve_image(filename):
    return send_from_directory('static/other_pic', filename)

@app.route('/error_page')
def error_page():
    return render_template('error_page.html')

@app.route('/')
def accueil():
    data_from_mongo = mongo.db.authors.find()
     # Récupérer les articles récents dans l'ordre décroissant de la date
    recent_posts = mongo.db.blogposts.aggregate([
        {
            '$lookup': {
                'from': 'authors',
                'localField': 'author_id',
                'foreignField': '_id',
                'as': 'author_info'
            }
        },
        {
            '$unwind': '$author_info'
        },
        {
            '$project': {
                'title': 1,
                'content': 1,
                'author_name': '$author_info.username',
                'author_profile_pic': '$author_info.picture_filename',
                'date': 1
            }
        },
        {
            '$sort': {'date': -1}  # Triez par date décroissante pour obtenir les articles récents en premier
        },
        {
            '$limit': 5  # Limitez le nombre d'articles affichés sur la page d'accueil
        }
    ])
    return render_template('index.html', data=data_from_mongo, recent_posts=recent_posts, author=current_user)

@app.route('/about')
def about():
    return render_template('about.html', author=current_user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        confirm_password = form.confirm_password.data

        # Vérifier si le mot de passe et le mot de passe de confirmation correspondent
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', category='danger')
            return redirect(url_for('signup'))

        existing_author = User.find_by_email(email)

        if existing_author is None:
            User.create_user(username, email, password)
            flash('Inscription réussie. Connectez-vous!', category='success')
            return redirect(url_for('accueil'))
        else:
            flash('L\'utilisateur existe déjà dans la base de données. Veuillez choisir un autre email.', 'danger')

    return render_template('signup.html', form=form, author=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('about'))

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Recherchez l'utilisateur dans la base de données
        author = User.find_by_email(email)

        if author and author.check_password(password):
            # Utilisez Flask-Login pour connecter l'utilisateur
            login_user(author)

            # Stockez l'ID de l'auteur dans la session
            session['author_id'] = str(author.id)

            flash('Connexion réussie!', category='success')
            return redirect(url_for('about'))
        else:
            flash('Échec de la connexion. Vérifiez vos informations d\'identification.', 'danger')

    return render_template('login.html', form=form, author=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnexion réussie!', 'success')
    return redirect(url_for('accueil'))

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = ArticleForm()

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data

        # Récupérer l'ID de l'auteur à partir de la session
        author_id = session.get('author_id')
        author_id = ObjectId(author_id)
        if author_id:
            # L'ID de l'auteur est dans la session, procédez à l'insertion
            blogposts = mongo.db.blogposts
            blogposts.insert_one({
                'title': title,
                'content': content,
                'author_id': author_id,  # Utilisez l'ID directement
                'date': datetime.utcnow()
            })

            flash('Article enregistré avec succès!', category='success')
            return redirect(url_for('create_post'))
        else:
            flash('L\'ID de l\'auteur n\'a pas été trouvé dans la session.', category='danger')

    # Pré-remplir le champ du formulaire avec l'ID de l'utilisateur connecté
    form.author_id.data = str(current_user.id)

    return render_template('create_post.html', form=form, author=current_user)

@app.route('/update_post/<post_id>', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = mongo.db.blogposts.find_one({'_id': ObjectId(post_id)})

    form = UpdatePostForm(obj=post)

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data

        mongo.db.blogposts.update_one({'_id': ObjectId(post_id)}, {'$set': {'title': title, 'content': content}})

        return redirect(url_for('author_post'))

    return render_template('update_post.html', form=form, author=current_user)

@app.route('/delete_post/<post_id>', methods=['GET','POST'])
@login_required
def delete_post(post_id):
    post = mongo.db.blogposts.find_one({'_id': ObjectId(post_id)})

    # Supprimer le post
    mongo.db.blogposts.delete_one({'_id': ObjectId(post_id)})
    flash("Le post a été supprimé avec succès.", 'success')

    return redirect(url_for('author_post'))

@app.route('/view_post/<post_id>')
def view_post(post_id):
    post = mongo.db.blogposts.find_one({'_id': ObjectId(post_id)})

    return render_template('view_post.html', post=post, author=current_user)

@app.route('/posts')
def posts():
    # Récupérez tous les articles avec les informations sur l'auteur
    blogposts = mongo.db.blogposts.aggregate([
        {
            '$lookup': {
                'from': 'authors',
                'localField': 'author_id',
                'foreignField': '_id',
                'as': 'author_info'
            }
        },
        {
            '$unwind': '$author_info'
        },
        {
            '$project': {
                'title': 1,
                'content': 1,
                'author_name': '$author_info.username',
                'author_profile_pic': '$author_info.picture_filename',
                'date': 1
            }
        }
    ])
    # La liste des images de profil des auteurs
    # author_profile_pic = {
    #     str(author['_id']): author.get('picture_filename', 'default_pic/profile.svg')  # Utilisez une image par défaut si 'picture_filename' n'existe pas
    #     for author in mongo.db.authors.find({}, {'_id': 1, 'picture_filename': 1})
    # }   

    return render_template('posts.html', blogposts=blogposts, author=current_user)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Vérifiez si l'image de profil existe avant de créer le chemin
    if current_user.picture_filename is not None:
        image_file = url_for('static', filename='author_profile_pic/' + current_user.picture_filename)
    else:
        # Fournir un chemin par défaut ou une image par défaut si l'image de profil n'est pas définie
        image_file = url_for('static', filename='default_pic/profile.svg')

    form = UpdateProfileForm()

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.age = form.age.data

        # Gérez le téléchargement de l'image (si fournie)
        if form.picture_filename.data and User.allowed_file(form.picture_filename.data.filename):
            picture_filename = form.picture_filename.data
            filename = secure_filename(picture_filename.filename)
            picture_filename.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.picture_filename = filename

        # Mettez à jour l'utilisateur dans la base de données
        result = mongo.db.authors.update_one(
            {'_id': ObjectId(current_user.id)},
            {
                '$set': {
                    'username': current_user.username,
                    'email': current_user.email,
                    'age': current_user.age,
                    'picture_filename': current_user.picture_filename
                }
            }
        )

        # Vérifiez si la mise à jour a été effectuée avec succès
        if result.modified_count > 0:
            flash('Your profile has been updated!', 'success')
        else:
            flash('No changes detected in your profile.', 'info')

        return redirect(url_for('profile'))

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.age.data = current_user.age

    return render_template('profile.html', form=form, image_file=image_file, author=current_user)


@app.route('/author_post')
@login_required
def author_post():
    # Récupérez tous les articles avec les informations sur l'auteur
    author_posts = mongo.db.blogposts.aggregate([
        {
            '$lookup': {
                'from': 'authors',
                'localField': 'author_id',
                'foreignField': '_id',
                'as': 'author_info'
            }
        },
        {
            '$unwind': '$author_info'
        },
        {
            '$match': {
                'author_info._id': ObjectId(current_user.id)
            }
        },
        {
            '$project': {
                'title': 1,
                'content': 1,
                'author_name': '$author_info.username',
                'author_profile_pic': '$author_info.picture_filename',
                'date': 1
            }
        }
    ])

    image_file = url_for('static', filename='author_profile_pic/' + current_user.picture_filename) if current_user.picture_filename else None
    return render_template('author_post.html', author_posts=author_posts, image_file=image_file, author=current_user)

if __name__ == '__main__':
    app.run(debug=True)
    app.run(debug=False, host='0.0.0.0')
