from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://messager_bbr6_user:N327COCI5sW4A3pQByOADiw1yvJEpehA@dpg-d9kd6fht0dsc739fl6og-a/messager_bbr6'
app.config["SECRET_KEY"] = "w"

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    sent_messages = db.relationship("Messages", foreign_keys="Messages.sender", back_populates="sender_user")
    received_messages = db.relationship("Messages", foreign_keys="Messages.recipient", back_populates="recipient_user")
    sent_requests = db.relationship("Friends", foreign_keys="Friends.sender", back_populates="sender_user")
    received_requests = db.relationship("Friends", foreign_keys="Friends.recipient", back_populates="recipient_user")

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)
    

class Friends(db.Model):
    __tablename__ = "friends"
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recipient = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.Boolean, default=False)

    sender_user = db.relationship("User", foreign_keys=[sender], back_populates="sent_requests")
    recipient_user = db.relationship("User", foreign_keys=[recipient], back_populates="received_requests")


class Messages(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recipient = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.Boolean, default=False)

    sender_user = db.relationship("User", foreign_keys=[sender], back_populates="sent_messages")
    recipient_user = db.relationship("User", foreign_keys=[recipient], back_populates="received_messages")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route("/")
@login_required
def index():
    return render_template("index.html", user=current_user.username)

@app.route("/login", methods=["GET", "POST"])
def login():
    error=""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            error="Wrong password or no user exists"

    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user:
            error = "User exists, you can login"
            return render_template("login.html", error=error)
        
        new_user = User(username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for("index"))

    return render_template("register.html")

@app.route("/search_friends", methods=["POST", "GET"])
@login_required
def search_friends():
    error=""
    if request.method == "POST":
        username = request.form.get("username")

        search_user = User.query.filter_by(username=username).first()

        if search_user:
            search_friend1 = Friends.query.filter_by(sender=search_user.id, recipient=current_user.id).first()
            search_friend2 = Friends.query.filter_by(sender=current_user.id, recipient=search_user.id).first()

            if not search_friend1 and not search_friend2:
                new_request = Friends(sender=current_user.id, recipient=search_user.id, status=False)
                db.session.add(new_request)
                db.session.commit()
            else:
                error = "There are pending request already"
        else:
            error = "No user with such username"
    return render_template("search_friends.html", error=error)

@app.route("/friends_requests")
@login_required
def friends_requests():
    all_requests = Friends.query.filter_by(recipient=current_user.id, status=False).all()
    return render_template("friends_requests.html", requests=all_requests)

@app.route("/friend_request_confirm", methods=["POST"])
@login_required
def friend_request_confirm():
    request_sender = request.form.get("id")
    select_request = Friends.query.filter_by(sender=request_sender, recipient=current_user.id, status=False).first()

    if not select_request:
        return "error"

    select_request.status = True
    db.session.commit()
    return redirect(url_for("friends_requests"))

@app.route("/friends")
@login_required
def friends():
    friends_sender = Friends.query.filter_by(sender=current_user.id, status=True).all()
    friends_recipient = Friends.query.filter_by(recipient=current_user.id, status=True).all()

    friends_names = [f.recipient_user.username for f in friends_sender] + [f.sender_user.username for f in friends_recipient]

    return render_template("friends.html", friends=friends_names)

@app.route("/message/<string:name>", methods=["POST", "GET"])
@login_required
def message(name):
    if request.method == "POST":
        text = request.form.get("text")
        search_user = User.query.filter_by(username=name).first()

        if not search_user:
            return "No user with that name"

        search_friend1 = Friends.query.filter_by(sender=search_user.id, recipient=current_user.id, status=True).first()
        search_friend2 = Friends.query.filter_by(sender=current_user.id, recipient=search_user.id, status=True).first()

        if search_friend1 or search_friend2:
            new_message = Messages(sender=current_user.id, recipient=search_user.id, message_text=text)
            db.session.add(new_message)
            db.session.commit()
        else:
            return "User is not your friend"

    return render_template("message.html")


@app.route("/messages")
@login_required
def messages():
    unread_messages = Messages.query.filter_by(recipient=current_user.id, status=False).all()

    unread_messages_dict = {}
    for message in unread_messages:
        unread_messages_dict[message.sender_user.username] = message.message_text
        message.status = True

    read_messages_dict = {}
    read_messages = Messages.query.filter_by(recipient=current_user.id, status=True).all()
    for message in read_messages:
        read_messages_dict[message.id] = message.sender_user.username, message.message_text

    
    db.session.commit()
    return render_template("messages.html", messages_unread=unread_messages_dict, messages_read=read_messages_dict)


with app.app_context():
    db.create_all()
