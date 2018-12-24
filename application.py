import os
import requests
from flask import Flask, session , render_template ,request ,redirect , url_for ,flash ,jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#index page- before login and after login
@app.route("/",methods=["GET","POST"])
def index():
	if request.method == "POST":
		username = request.form.get("username")
		password = request.form.get("password")
		test = db.execute("SELECT username,email,password FROM users WHERE username=:username OR email=:email",
				{"username":username,"email":username}).fetchall()
		if test:
			if test[0][2] == password:
				session['user']=test[0][0]
				return redirect(url_for('index'))
			else:
				return render_template('index.html',message="Wrong password")
		else:
			return render_template('index.html',message="Wrong Username/Email")
		db.commit()

	if session:
		try:
			return render_template("sindex.html",username=session['user'].capitalize(),searchquery="Initial")
		except:
			session.clear()
			return redirect(url_for('index'))
	return render_template('index.html')

#register page - existing user check and redirect to sindex for logged users
@app.route("/register", methods=["GET","POST"])
def register():
	if request.method == "GET":
		if session:
			return redirect(url_for('index'))
		return render_template("register.html",message="Passwords must match")
	else:
		username = request.form.get("username")
		email = request.form.get("email")
		password = request.form.get("password")
		cpassword = request.form.get("cpassword")
		if password == cpassword:
			if db.execute("SELECT username,email FROM users WHERE username=:username OR email=:email",
				{"username":username,"email":email}).rowcount==0:
				db.execute("INSERT INTO users (username,email,password) VALUES (:username,:email,:password)",
					{"username":username,"email":email,"password":password})
				db.commit()
				return render_template("index.html",message="user created")
			else:
				return render_template("register.html",message="username/email already exists",message1="passwords must match")

		else:
			return render_template("register.html",message="passwords didn't match",message1="passwords must match")

#logout function for logged in users
@app.route("/logout")
def logout():
	session.clear()
	return redirect(url_for('index'))

#query
@app.route("/query",methods=["POST","GET"])
def query():
	if session:
		if request.method == "POST":
			query = "%"+request.form.get("query")+"%"
			if db.execute("SELECT * FROM books WHERE isbn ILIKE :isbn OR title ILIKE :title OR author ILIKE :author OR year ILIKE :year",
				{"isbn":query,"title":query,"author":query,"year":query}).rowcount==0:
				return render_template("sindex.html",searchquery="Nothing Found",username=session['user'])
			searchquery = db.execute("SELECT * FROM books WHERE isbn ILIKE :isbn OR title ILIKE :title OR author ILIKE :author OR year ILIKE :year",
				{"isbn":query,"title":query,"author":query,"year":query}).fetchall()
			db.commit()
			return render_template("sindex.html",searchquery=searchquery,username=session['user'].capitalize())
		else:
			return render_template("sindex.html",searchquery="Initial",username=session['user'].capitalize())

#book page.
@app.route("/query/<isbn>",methods=["GET","POST"])
def book(isbn):
	if session:
		if request.method == "GET":
			var= db.execute("SELECT * FROM books WHERE isbn=:isbn",{"isbn":isbn}).fetchall()
			reviews = db.execute("SELECT username,review,rating FROM reviews WHERE isbn=:isbn",
				{"isbn":isbn}).fetchall()
			review = db.execute("SELECT username,review,rating FROM reviews WHERE isbn=:isbn AND username ILIKE :username",
				{"isbn":isbn,"username":session['user']}).fetchall()
			res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":"Jrprke1BLqA0yaV0fXl6g", "isbns":isbn})
			return render_template("book.html",var=var,review=review,reviews=reviews,res=res.json(),username=session['user'].capitalize())
		if request.method == "POST":
			rating = request.form.get('rating')
			userreview = request.form.get('userreview')
			db.execute("INSERT INTO reviews (review,rating,username,isbn) VALUES (:review,:rating,:username,:isbn)",
				{"review":userreview,"rating":rating,"username":session['user'],"isbn":isbn})
			db.commit()
			return redirect(url_for('book',isbn=isbn))
	return redirect(url_for('index'))

#API PAGE
@app.route("/api/<isbn>")
def api(isbn):
	book = db.execute("SELECT * FROM books WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
	stat = db.execute("SELECT COUNT(rating),AVG(rating) FROM reviews WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
	db.commit()
	if book:
		if stat.count:
			return jsonify(isbn=book.isbn,
				title=book.title,
				author=book.author,
				year=int(book.year),
				ratings_count=stat.count,
				average_rating= round(float(stat.avg),2))
		else:
			return jsonify(isbn=book.isbn,
				title=book.title,
				author=book.author,
				year=int(book.year),
				ratings_count  = stat.count,
				average_rating = 0)
	return page_not_found(404)

#Error Page
@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404

