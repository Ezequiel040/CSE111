import sqlite3
from datetime import datetime
from sqlite3 import Error
from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
from flask import Flask, render_template
from flask import request, jsonify, send_from_directory
from flask import redirect, url_for, session, flash
import os
import random
from werkzeug.utils import secure_filename
from passlib.hash import sha256_crypt
from functools import wraps

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('You must be logged in to access this page.')
            return redirect(url_for('sign_in'))
        return f(*args, **kwargs)
    return decorated_function


# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
# Folder where uploaded images will be stored
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/submit-post', methods=['GET', 'POST'])
@login_required
def submit_post():
    if 'image' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['image']
    question = request.form.get('question')
    answer = request.form.get('answer')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file to the uploads folder
        file.save(file_path)

        # Save the post data to the database
        conn = get_db_connection()
        try:
            user_id = session['user_id']  # Assume user_id is stored in the session after login
            fun_fact = question  # Example placeholder
            age = 18  # Example age; replace with actual data if needed
            key_word = answer  # Using the answer as a key word for simplicity

            # Use a cursor to execute SQL statements
            cursor = conn.cursor()

            # Insert the post into the Post table
            cursor.execute(
                "INSERT INTO Post (user_id, file_path, fun_fact, age, key_word) VALUES (?, ?, ?, ?, ?)",
                (user_id, filename, fun_fact, age, key_word)
            )
            post_id = cursor.lastrowid

            # Insert the puzzle into the Puzzle table
            cursor.execute(
                "INSERT INTO Puzzle (key_word, lvl_req, pic_id) VALUES (?, ?, ?)",
                (key_word, 1, post_id)  # Example level requirement
            )
            # Increment the posts column in the User table
            cursor.execute(
                "UPDATE User SET posts = posts + 1 WHERE user_id = ?",
                (user_id,)
            )

            # Commit the transaction
            conn.commit()

            flash('Post created successfully!')
            return redirect(url_for('home'))
        except sqlite3.Error as e:
            print(e)
            flash('An error occurred while saving your post.')
            conn.rollback()
        finally:
            conn.close()
    else:
        flash('Invalid file type. Only images are allowed.')

    return redirect(url_for('home'))


DATABASE = 'Checkpoint2-dbase.sqlite3'

# Helper function to open database connection
def get_db_connection():
    try:
        conn = sqlite3.connect('Checkpoint2-dbase.sqlite3')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

conn = sqlite3.connect('Checkpoint2-dbase.sqlite3')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='User'")
table_exists = c.fetchone()

def openConnection(_dbFile):
    print("++++++++++++++++++++++++++++++++++")
    print("Open database: ", _dbFile)

    conn = None
    try:
        conn = sqlite3.connect(_dbFile)
        print("success")
    except Error as e:
        print(e)

    print("++++++++++++++++++++++++++++++++++")

    return conn

def closeConnection(_conn, _dbFile):
    print("++++++++++++++++++++++++++++++++++")
    print("Close database: ", _dbFile)

    try:
        _conn.close()
        print("success")
    except Error as e:
        print(e)

    print("++++++++++++++++++++++++++++++++++")

if not table_exists:
    c.execute("""CREATE TABLE User(
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        userName TEXT UNIQUE,
        password TEXT,
        posts INTEGER,
        posts_solved INTEGER
    )""")

    # Create Post table
    c.execute("""CREATE TABLE Post(
        pic_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        file_path TEXT NOT NULL,
        upload_date TEXT,
        fun_fact TEXT,
        age INTEGER,
        key_word TEXT,
        FOREIGN KEY (user_id) REFERENCES User(user_id)
    )""")

    # Create Puzzle table 
    # comment: is pic id foreign since it comes from post table
    c.execute("""CREATE TABLE Puzzle(
        puzzle_id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_word TEXT NOT NULL, 
        lvl_req INTEGER NOT NULL,
        pic_id INTEGER,
        FOREIGN KEY (pic_id) REFERENCES Post(pic_id)
    )""")

    # Create Solved table
    c.execute("""CREATE TABLE Solved(
        sol_id INTEGER PRIMARY KEY AUTOINCREMENT,
        puzzle_id INTEGER,
        user_id INTEGER,
        solved_at TEXT,
        FOREIGN KEY (puzzle_id) REFERENCES Puzzle(puzzle_id),
        FOREIGN KEY (user_id) REFERENCES User(user_id)
    )""")

    # Create Likes table
    c.execute("""CREATE TABLE Likes(
        like_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pic_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES User(user_id),
        FOREIGN KEY (pic_id) REFERENCES Post(pic_id)
    )""")

    # Create Progress table
    c.execute("""CREATE TABLE Progress(
        user_id INTEGER PRIMARY KEY,
        curr_lvl INTEGER NOT NULL,
        exp_points INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES User(user_id)
    )""")





conn.commit()
conn.close()
@app.route('/')
def start():
    return render_template("sign_in.html")


@app.route('/home')
@login_required
def home():
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Get the current user's ID from the session
        current_user_id = session['user_id']

        # Select puzzles that are not posted by the current user and not solved by the current user
        c.execute('''
            SELECT Puzzle.puzzle_id, Post.fun_fact, Post.file_path, Post.pic_id
            FROM Puzzle 
            JOIN Post ON Puzzle.pic_id = Post.pic_id
            WHERE Post.user_id != ?
            AND Puzzle.puzzle_id NOT IN (
                SELECT Solved.puzzle_id 
                FROM Solved 
                WHERE user_id = ?
            )
        ''', (current_user_id, current_user_id))
        puzzles = c.fetchall()



        if puzzles:
            random_puzzle = random.choice(puzzles)
            puzzle_id = random_puzzle[0]
            puzzle_question = random_puzzle[1]
            puzzle_image_path = random_puzzle[2]
            pic_id = random_puzzle[3]

            # Retrieve the like count for this pic_id
            c.execute('SELECT COUNT(*) FROM Likes WHERE pic_id = ?', (pic_id,))
            like_count = c.fetchone()[0]
            conn.close()

            session['pic_id'] = pic_id


            return render_template(
                'main.html',
                username=session.get('username', 'User'),
                puzzle_id=puzzle_id,
                puzzle_question=puzzle_question,
                puzzle_image_path=puzzle_image_path,
                pic_id = pic_id,
                like_count = like_count

            )
        else:
            flash('No puzzles available. Try creating one!')
            return render_template(
                'main.html',
                username=session.get('username', 'User'),
                puzzle_id=None,
                puzzle_question="No puzzle available",
                puzzle_image_path="placeholder.jpg",
                # pic_id=None,
                # like_count=0
            )
    except sqlite3.Error as e:
        print(e)
        conn.close()
        flash('An error occurred while loading the puzzle.')
        return render_template(
            'main.html',
            username=session.get('username', 'User'),
            puzzle_id=None,
            puzzle_question="Error loading puzzle",
            puzzle_image_path="placeholder.jpg",
            # pic_id=None,
            # like_count=0
        )

# in the main html

@app.route('/post', methods=['GET'])
@login_required
def post_page():
    return render_template('post.html')

@app.route('/submit-answer', methods=['POST'])
@login_required
def submit_answer():
    # Get the submitted puzzle ID and answer
    puzzle_id = request.form.get('puzzle_id')
    user_answer = request.form.get('puzzle_answer')
    
    # Fetch the user ID from the session (assuming session contains user_id)
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to submit an answer!')
        return redirect(url_for('sign_in'))

    conn = get_db_connection()
    c = conn.cursor()

    try:
        # fetches ID of user to later level up
        c.execute('SELECT user_id FROM Progress WHERE user_id = ?', (user_id,))
        progress = c.fetchone()

        if not progress:
            # Add user_id to the Progress table with an initial level of 0
            print(f"User {user_id} not found in Progress table. Adding user with level 0.")
            c.execute('INSERT INTO Progress (user_id, curr_lvl, exp_points) VALUES (?, ?, ?)', (user_id, 0, 0))
            conn.commit()

        # Fetch the correct answer for the puzzle
        c.execute('SELECT key_word FROM Puzzle WHERE puzzle_id = ?', (puzzle_id,))
        correct_answer = c.fetchone()

        if correct_answer:
            correct_answer = correct_answer[0].strip().lower()
            user_answer = user_answer.strip().lower()

            if user_answer == correct_answer:
                # Answer is correct
                print(f"User {user_id} submitted the correct answer for puzzle {puzzle_id}.")
                flash('Correct! You solved the puzzle.')
                
                            # Increment the posts column in the User table
                c.execute(
                "UPDATE User SET posts_solved = posts_solved + 1 WHERE user_id = ?",
                (user_id,)
                )

                # Update the user's level
                c.execute('UPDATE Progress SET curr_lvl = curr_lvl + 1 WHERE user_id = ?', (user_id,))

                # Add an entry to the Solved table
                from datetime import datetime
                solved_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                c.execute(
                    'INSERT INTO Solved (puzzle_id, user_id, solved_at) VALUES (?, ?, ?)',
                    (puzzle_id, user_id, solved_at)
                )
                conn.commit()
            else:
                # Answer is incorrect
                print(f"User {user_id} submitted an incorrect answer for puzzle {puzzle_id}.")
                flash('Incorrect. Try again!')
        else:
            print(f"Puzzle ID {puzzle_id} not found.")
            flash('Puzzle not found.')

        return redirect(url_for('home'))

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('An error occurred while submitting your answer.')
        return redirect(url_for('home'))
    
    finally:
        conn.close()



@app.route('/like-post', methods=['POST'])
@login_required
def like_post():
    user_id = session['user_id']  # Get the current user's ID from the session
    pic_id = request.form.get('pic_id')  # Get the pic_id from form data

    if not pic_id:
        return "", 204  # Return an empty response if pic_id is missing

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if the user has already liked this post
        cursor.execute("SELECT * FROM Likes WHERE user_id = ? AND pic_id = ?", (user_id, pic_id))
        existing_like = cursor.fetchone()

        if not existing_like:
            # Add a new like to the Likes table
            cursor.execute("INSERT INTO Likes (user_id, pic_id) VALUES (?, ?)", (user_id, pic_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error while liking the post: {e}")
        conn.rollback()
    finally:
        conn.close()

    return "", 204  # Return a minimal response (HTTP 204: No Content)



@app.route('/register')
def register():
    return render_template('create_acct.html')

@app.route('/sign_in')
def sign_in():
    return render_template('sign_in.html')

@app.route('/profile')
@login_required
def profile():
    if 'username' not in session:
        return redirect(url_for('sign_in'))
    # print(username)

    username = session['username']
    conn = sqlite3.connect('Checkpoint2-dbase.sqlite3')
    cursor = conn.cursor()
    
    # Fetch user details from the database like num of posts and num of posts solved
    cursor.execute('''
        SELECT posts, posts_solved
        FROM User
        WHERE userName = ?
    ''', (username,))  # Use 'userName' as per the schema
    result = cursor.fetchone()
    conn.close()
    
    if result:
        posts, posts_solved = result
        return render_template(
            'profile.html',
            username=username,
            posts=posts,
            posts_solved=posts_solved
        )
    else:
        return "User not found", 404

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Optionally, redirect to a safe page like the login page
    return redirect(url_for('sign_in'))




@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '').strip()
    results = []

    if query:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # searches for posts based on fun fact answer
            cursor.execute('''
                SELECT Post.key_word, Post.file_path, User.username
                FROM Post
                JOIN User ON Post.user_id = User.user_id
                WHERE Post.key_word LIKE ?
            ''', (f'%{query}%',))
            results = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

    formatted_results = [
        {'fun_fact': row[0], 'file_path': row[1], 'username': row[2]}
        for row in results
    ]

    return render_template('search.html', results=formatted_results)



# 1. Register a new user
@app.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')  # Get username from the form
    password = request.form.get('password')  # Get password from the form

    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400

    # Hash the password
    hashed_password = sha256_crypt.hash(password)

    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Insert the new user into the database
        c.execute('''
            INSERT INTO User (username, password, posts, posts_solved)
            VALUES (?, ?, ?, ?)
        ''', (username, hashed_password, 0, 0))
        
        conn.commit()
        conn.close()
        # return jsonify({'message': 'User added successfully'}), 201
        return redirect(url_for('sign_in'))

    except sqlite3.IntegrityError:
        # Handle duplicate username errors or other constraints
        return jsonify({'error': 'Username already exists'}), 409

    except Exception as e:
        # Handle other potential errors
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Validate input
    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor()

    # Check if the user exists
    cursor.execute('SELECT user_id, password FROM User WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()

    if result:
        user_id, stored_password = result
        # verify passwrd
        if sha256_crypt.verify(password, stored_password):
            # Log the user in
            session['user_id'] = user_id
            session['username'] = username
            session['logged_in'] = True
            return redirect(url_for('profile'))  # Replace with your main page route
        else:
            flash('Invalid username or password')
            # return jsonify({'error': 'Invalid username or password'}), 401
    else:
        return jsonify({'error': 'User not found'}), 404
    return redirect(url_for('sign_in'))


#3
def delete_post(conn, user_id, pic_id):
    print("++++++++++++++++++++++++++++++++++")
    try:

        c = conn.cursor()
        c.execute('''
                DELETE
                FROM Post
                WHERE user_id = ? AND pic_id = ?
                ''', (user_id, pic_id))
        conn.commit()
    except Error as e:
        print(e)

    print("++++++++++++++++++++++++++++++++++")


#4 get posts liked by user ###
def get_likes_by_user(conn,user_id):
    print("++++++++++++++++++++++++++++++++++")
    try:
        c = conn.cursor()
        c.execute('''
                SELECT like_id
                FROM Likes
                WHERE user_id = ?          
                ''',(user_id,))
        likes = c.fetchall()
        print("#4", likes)
        conn.commit()
    except Error as e:
        print(e)

    print("++++++++++++++++++++++++++++++++++")

#5 Get all puzzles solved by a specific user
def user_solved_puzzles(conn, user_id):
    print("++++++++++++++++++++++++++++++++++")
    try:
        c = conn.cursor()
        c.execute('''
                SELECT puzzle_id
                FROM Solved
                WHERE user_id = ?
                ''', (user_id,))
        solved = c.fetchall()
        print("#5", solved)
        conn.commit()
    except Error as e:
        print(e)

    print("++++++++++++++++++++++++++++++++++")

#6 Insert a new puzzle and solve record for a user: 
# would be used in tandem w/ creating a post since u need to make the puzzle along w the post
def insert_puzzle(conn, pic_id,key_word,lvl_req):
    print("++++++++++++++++++++++++++++++++++")
    try:
        c = conn.cursor()
        c.execute = ('''
                    INSERT INTO Puzzle(key_word, lvl_req, pic_id)
                    VALUES(?,?,?)
                    ''', (pic_id,key_word,lvl_req))
        conn.commit()
    except Error as e:
        print(e)

    print("++++++++++++++++++++++++++++++++++")


@app.route('/leader')
@login_required
def leaderboard():
    conn = sqlite3.connect('Checkpoint2-dbase.sqlite3')
    cursor = conn.cursor()

    try:
        # Top 5 Players
        cursor.execute('''
            SELECT User.userName, Progress.curr_lvl
            FROM User
            JOIN Progress ON User.user_id = Progress.user_id
            ORDER BY Progress.curr_lvl DESC
            LIMIT 5
        ''')
        top_players = cursor.fetchall()

        # Top 5 Posts by Likes
        cursor.execute('''
            SELECT Post.pic_id, Post.file_path, User.userName, COUNT(Likes.like_id) AS like_count
            FROM Post
            LEFT JOIN Likes ON Post.pic_id = Likes.pic_id
            JOIN User ON Post.user_id = User.user_id
            GROUP BY Post.pic_id
            ORDER BY like_count DESC
            LIMIT 5
        ''')
        top_posts = cursor.fetchall()

        # Top 5 Most Solved Puzzles
        cursor.execute('''
            SELECT Puzzle.puzzle_id, Post.file_path, User.userName, COUNT(Solved.sol_id) AS solve_count
            FROM Puzzle
            LEFT JOIN Solved ON Puzzle.puzzle_id = Solved.puzzle_id
            JOIN Post ON Puzzle.pic_id = Post.pic_id
            JOIN User ON Post.user_id = User.user_id
            GROUP BY Puzzle.puzzle_id
            ORDER BY solve_count DESC
            LIMIT 5
        ''')
        most_solved_puzzles = cursor.fetchall()

        conn.close()

        # Format data for rendering
        formatted_top_posts = [
            {
                "pic_id": post[0],
                "file_path": post[1],
                "username": post[2],
                "like_count": post[3],
            }
            for post in top_posts
        ]
        formatted_most_solved_puzzles = [
            {
                "puzzle_id": puzzle[0],
                "file_path": puzzle[1],
                "username": puzzle[2],
                "solve_count": puzzle[3],
            }
            for puzzle in most_solved_puzzles
        ]

        return render_template(
            'leaderboard.html',
            top_players=top_players,
            top_posts=formatted_top_posts,
            most_solved_puzzles=formatted_most_solved_puzzles,
        )
    except sqlite3.Error as e:
        conn.close()
        print("Database error:", e)
        return "An error occurred while retrieving the leaderboard data", 500




@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    user_id = session['user_id']
    conn = get_db_connection()
    try:
        # Delete all user-related data
        delete_user(conn, user_id)
        conn.close()
        session.clear()  # Log the user out after account deletion
        flash("Account deleted successfully.")
        return redirect(url_for('sign_in'))
    except sqlite3.Error as e:
        print(e)
        conn.rollback()
        conn.close()
        flash("An error occurred while deleting the account.")
        return redirect(url_for('profile'))


@app.route('/delete-posts')
@login_required
def delete_posts():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pic_id, file_path, fun_fact FROM Post WHERE user_id = ?", (user_id,))
    user_posts = cursor.fetchall()
    conn.close()
    return render_template('delete_post.html', posts=user_posts)

#links back to the button in the delete post page
@app.route('/delete-post/<int:pic_id>', methods=['POST'])
@login_required
def delete_post_route(pic_id):
    # Get the user_id from the session (assuming session stores user_id)
    user_id = session.get('user_id')

    if not user_id:
        flash('You must be logged in to delete a post!')
        return redirect(url_for('sign_in'))
    
    conn = get_db_connection()
    c = conn.cursor()
    try:
        delete_post(conn, user_id, pic_id)
        c.execute('''
                     UPDATE User
                    SET posts= posts - 1
                    WHERE user_id = ?
                    ''', (user_id,) )
        conn.commit()

        flash('Post deleted successfully!')
    except Exception as e:
        print(f"Error while deleting post: {e}")
        flash('An error occurred while deleting the post.')
    finally:
        conn.close()
    
    return redirect(url_for('profile'))



#13 top 10 newest posts
def recent_posts(conn):
    print("++++++++++++++++++++++++++++++++++")
    print("")
    try:
        c = conn.cursor()
        c.execute('''
                  SELECT pic_id, file_path, upload_date
                  FROM Post
                  ORDER BY upload_date DESC
                  LIMIT 10
                  ''')
        new = c.fetchall()
        print("New: ", new)
        conn.commit()
    
    except Error as e:
        print(e)

    print("++++++++++++++++++++++++++++++++++")

#14 del user
def delete_user(conn, user_id):
    print("++++++++++++++++++++++++++++++++++")
    print("")
    try:
        c = conn.cursor()
        c.execute('''
            DELETE FROM Solved WHERE user_id = ?
        ''', (user_id,))
        c.execute('''
            DELETE FROM Likes WHERE user_id = ?
        ''', (user_id,))
        c.execute('''
            DELETE FROM Post WHERE user_id = ?
        ''', (user_id,))
        c.execute('''
            DELETE FROM Progress WHERE user_id = ?
        ''', (user_id,))
        c.execute('''
            DELETE FROM User WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
    except Error as e:
        print(e)

    print("++++++++++++++++++++++++++++++++++")



# sample data
def insert_sample_data(conn):
    c = conn.cursor()

    # Clear existing data
    # c.execute("DELETE FROM Progress")
    # c.execute("DELETE FROM Solved")
    # c.execute("DELETE FROM Likes")
    # c.execute("DELETE FROM Puzzle")
    # c.execute("DELETE FROM Post")
    # c.execute("DELETE FROM User")

    # # Reset auto-increment counters if needed (SQLite specific)
    # c.execute("DELETE FROM sqlite_sequence WHERE name='Progress'")
    # c.execute("DELETE FROM sqlite_sequence WHERE name='Solved'")
    # c.execute("DELETE FROM sqlite_sequence WHERE name='Likes'")
    # c.execute("DELETE FROM sqlite_sequence WHERE name='Puzzle'")
    # c.execute("DELETE FROM sqlite_sequence WHERE name='Post'")
    # c.execute("DELETE FROM sqlite_sequence WHERE name='User'")

    # Insert sample users
    c.execute("INSERT INTO User (userName, password, posts, posts_solved) VALUES ('alice', 'password123', 5, 2)")
    c.execute("INSERT INTO User (userName, password, posts, posts_solved) VALUES ('bob', 'securePass', 3, 1)")
    c.execute("INSERT INTO User (userName, password, posts, posts_solved) VALUES ('carol', 'myPassword', 4, 3)")

    # Insert sample posts
    c.execute("INSERT INTO Post (user_id, file_path, upload_date, fun_fact, age, key_word) VALUES (1, 'images/image1.png', ?, 'Alice loves hiking', 30, 'hiking')", (datetime.now().strftime('%Y-%m-%d'),))
    c.execute("INSERT INTO Post (user_id, file_path, upload_date, fun_fact, age, key_word) VALUES (2, 'images/image2.png', ?, 'Bob is a cat person', 25, 'cats')", (datetime.now().strftime('%Y-%m-%d'),))
    c.execute("INSERT INTO Post (user_id, file_path, upload_date, fun_fact, age, key_word) VALUES (3, 'images/image3.png', ?, 'Carol enjoys painting', 28, 'painting')", (datetime.now().strftime('%Y-%m-%d'),))

    # Insert sample puzzles
    c.execute("INSERT INTO Puzzle (key_word, lvl_req, pic_id) VALUES ('hiking', 1, 1)")
    c.execute("INSERT INTO Puzzle (key_word, lvl_req, pic_id) VALUES ('cats', 1, 2)")
    c.execute("INSERT INTO Puzzle (key_word, lvl_req, pic_id) VALUES ('painting', 1, 3)")

    # Insert sample solved puzzles
    c.execute("INSERT INTO Solved (puzzle_id, user_id, solved_at) VALUES (1, 2, ?)", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
    c.execute("INSERT INTO Solved (puzzle_id, user_id, solved_at) VALUES (2, 3, ?)", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
    c.execute("INSERT INTO Solved (puzzle_id, user_id, solved_at) VALUES (3, 1, ?)", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))

    # Insert sample likes
    c.execute("INSERT INTO Likes (user_id, pic_id) VALUES (1, 2)")
    c.execute("INSERT INTO Likes (user_id, pic_id) VALUES (2, 1)")
    c.execute("INSERT INTO Likes (user_id, pic_id) VALUES (3, 1)")
    c.execute("INSERT INTO Likes (user_id, pic_id) VALUES (1, 3)")

    # Insert sample progress
    # c.execute("INSERT INTO Progress (user_id, curr_lvl, exp_points) VALUES (1, 2, 100)")
    # c.execute("INSERT INTO Progress (user_id, curr_lvl, exp_points) VALUES (2, 1, 50)")
    # c.execute("INSERT INTO Progress (user_id, curr_lvl, exp_points) VALUES (3, 3, 150)")

    # Commit the inserts
    conn.commit()
    print("Sample data inserted successfully.")


def main():
    database = r"Checkpoint2-dbase.sqlite3"

    conn = openConnection(database)


    closeConnection(conn, database)


if __name__ == '__main__':
    main()
    app.run(debug=True)

    







