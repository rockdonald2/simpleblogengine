import mysql.connector
from datetime import datetime

db = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    passwd = 'root',
    database = 'testdatabase'
)

""" mycursor = db.cursor() """

# we create the database and update the connection arguments
""" mycursor.execute('CREATE DATABASE testdatabase') """

# we create Person table, which will store Person instances
""" mycursor.execute('CREATE TABLE Person (name VARCHAR(50), age smallint UNSIGNED, personID int PRIMARY KEY AUTO_INCREMENT)') """

# describes the Person table
""" mycursor.execute('DESCRIBE Person') """

# we make the change
""" mycursor.execute('INSERT INTO Person (name, age) VALUES (%s, %s)', ('Tim', 19)) """
# then we commit it to take effect
""" db.commit() """

# we make the change
""" mycursor.execute('INSERT INTO Person (name, age) VALUES (%s, %s)', ('Zsolt', 20)) """
# then we commit it to take effect
""" db.commit() """

""" mycursor.execute('SELECT * FROM Person') """

# print the previous describe/select command's output
""" for x in mycursor:
    print(x) """

# we clear the previous table
""" mycursor.execute('DROP TABLE Person') """

# we create a new table
""" mycursor.execute('CREATE TABLE Test (name varchar(50) NOT NULL, created datetime NOT NULL, gender ENUM("M", "F", "O") NOT NULL, id int PRIMARY KEY NOT NULL AUTO_INCREMENT)') """

""" mycursor.execute('INSERT INTO Test (name, created, gender) VALUES (%s, %s, %s)', ('Zsolt', datetime.now(), 'F'))
db.commit() """

""" mycursor.execute('SELECT id, name FROM Test WHERE gender = "M" ORDER BY id DESC') """

""" for x in mycursor:
    print(x) """

# we add a new column to an already existing table
""" mycursor.execute('ALTER TABLE Test ADD COLUMN food VARCHAR(50) NOT NULL') """

# we drop it
""" mycursor.execute('ALTER Table Test DROP food') """

""" mycursor.execute('DESCRIBE Test')

for x in mycursor:
    print(x) """

users = [('zsolt', '12345'),
    ('joe', 'password123'),
    ('sarah', 'pass234')]

user_scores = [(45, 100), (30, 200), (46, 124)]
cursor = db.cursor()

""" Q1 = 'CREATE TABLE Users (id int PRIMARY KEY NOT NULL AUTO_INCREMENT, name varchar(50) NOT NULL, pwd VARCHAR(50) NOT NULL)'
Q2 = 'CREATE TABLE Scores (userId int PRIMARY KEY, FOREIGN KEY(userId) REFERENCES Users(id), game1 int DEFAULT 0 NOT NULL, game2 int DEFAULT 0 NOT NULL)' """

""" cursor.execute(Q1)
cursor.execute(Q2) """

""" cursor.execute('DESCRIBE Scores') """

""" for x in cursor:
    print(x) """

""" Q3 = 'INSERT INTO Users (name, pwd) VALUES (%s, %s)'
Q4 = 'INSERT INTO Scores (userId, game1, game2) VALUES (%s, %s, %s)' """

""" for x, user in enumerate(users):
    cursor.execute(Q3, user)
    last_id = cursor.lastrowid
    cursor.execute(Q4, (last_id,) + user_scores[x]) """

""" db.commit() """

""" cursor.execute('SELECT * FROM Scores') """

""" for x in cursor:
    print(x) """

""" cursor.execute('SELECT * FROM Users') """

""" for x in cursor:
    print(x) """