import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from datetime import datetime, timezone
import bcrypt

load_dotenv()

#returns connection object
def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        cursor_factory = psycopg2.extras.RealDictCursor
    )

#returns list of all users
def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, surname, login, mail, created FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

#returns user object by login
def get_user_by_login(login: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, surname, login, mail, password, role FROM users WHERE login = %s",
                 (login,))
    userrow = cur.fetchone()
    cur.close()
    conn.close()
    return userrow

#returns user object by id
def get_user_by_id(userid: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, surname, login, mail, role FROM users WHERE id = %s",
                 (userid,))
    userrow = cur.fetchone()
    cur.close()
    conn.close()
    return userrow

#returns id of added user
def add_user(name: str, surname: str, login: str, mail: str, password: str, role="user"):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashedstr = hashed.decode('utf-8')

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (name, surname, login, mail, password, role) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (name, surname, login, mail, hashedstr, role)
        )
        user_id = cur.fetchone()["id"]
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        user_id = None
    finally:
        cur.close()
        conn.close()
    return user_id

#returns id of added conversation
def add_conversation(userid: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (user_id) VALUES (%s) RETURNING id",
        (userid,)
    )
    convid = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return convid

#returns list of conversations filtered by user
def get_conversations_by_user(userid: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, created FROM conversations WHERE user_id = (%s)",
        (userid,)
    )
    userconvs = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return userconvs

#returns list of all conversations
def get_all_conversations():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, created FROM conversations")
    convs = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return convs

#returns id of added history
def add_history(conversationid: int, usermessage: str, llmmessage: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO history (conversation_id, usermessage, llmmessage) VALUES (%s, %s, %s) RETURNING id",
        (conversationid, usermessage, llmmessage)
    )
    histid = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return histid

#returns numer of affected rows (1 row = history rate updated, 0 row = couldn't find history)
def add_history_rate(historyid: int, rate: bool):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE history SET rating = %s WHERE id = %s",
            (rate, historyid)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return cur.rowcount

#returns list of history filtered by conversation id
def get_history(conversationid: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, usermessage, llmmessage, rating, created FROM history WHERE conversation_id = (%s) ORDER BY created ASC",
        (conversationid,)
    )
    history = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return history

#returns conversation id by history id
def get_conversation_by_history(historyid: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, conversation_id FROM history WHERE id = (%s)",
        (historyid,)
    )
    history = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return history

#no return
def add_refresh_token(userid: int, token: str, expiredat: datetime):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO refresh_tokens (user_id, token, created_at, expires_at, revoked) VALUES (%s, %s, %s, %s, FALSE);",
         (userid, token, datetime.utcnow(), expiredat))
    conn.commit()
    cur.close()
    conn.close()

#resturns token object
def get_refresh_token(token: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, token, created_at, expires_at, revoked FROM refresh_tokens WHERE token = %s ORDER BY created_at DESC;",
         (token,))
    refreshtoken = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return refreshtoken

#returns numer of affected rows (1 row = token revoke updated, 0 row = couldn't find token)
def revoke_refresh_token(token: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE refresh_tokens SET revoked = TRUE WHERE token = %s;",
            (token,))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return cur.rowcount

#returns refresh token object by user
def get_active_refresh_token_by_user(userid: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, token, created_at, expires_at, revoked FROM refresh_tokens WHERE user_id = %s AND revoked = FALSE AND expires_at > %s ORDER BY created_at DESC LIMIT 1;",
                 (userid, datetime.now(timezone.utc)))
    tokenobj = cur.fetchone()
    cur.close()
    conn.close()
    return tokenobj