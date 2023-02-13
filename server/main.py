from typing import Union, Optional, List
from fastapi import FastAPI, Path, Query, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

#---LOCAL IMPORTS---#
from models import User, Thought, Token, TokenData, UserInDB
from db import get_thoughts, get_users, create_user, get_user_by_email, get_user_by_username, create_thought

#---LOAD ENV VARS---#
load_dotenv()

#---SECURITY SETUP---#
SECRET_KEY = os.environ.get('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes =["bcrypt"], deprecated="auto")
oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="token")

#---APP INIT---#
app = FastAPI()

#---DB INIT FROM DB MODULE---#
db = get_users()

def verify_password(plain_text_pw, hash_pw):
    return pwd_context.verify(plain_text_pw, hash_pw)

def get_user(db, username:str):
    if username in db:
        user_data = db[username]
        return UserInDB(**user_data)

def authenticate_user(db, username:str, password:str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_pw):
        return False
    return user

def create_access_token(data:dict, expires_delta:timedelta or None = None):
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow()() + timedelta(minutes = 60)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)
    return encoded_jwt

async def get_current_user(token : str = Depends(oauth_2_scheme)):
    credential_exception = HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail= "Could not validate credentials",
                                         headers={"WWW-Authenticate":"Bearer"})
    
    try:
        payload = jwt.decode(token, SECRET_KEY,algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credential_exception
        token_data = TokenData(username=username)
    
    except JWTError:
        raise credential_exception
    
    user=get_user(db, username = token_data.username)
    
    if user is None:
        raise credential_exception
    
    return user

#---optional to check if user status is disabled---#
async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail = "Inactive user!")
    return current_user
    



#---ENDPOINTS---#
@app.get("/")
def read_root():
    raise HTTPException(status_code=400, detail = "Calling on the root page is not allowed!")

@app.get("/api/v1/users")
async def get_all_users():
    return get_users()

@app.get("/api/v1/thoughts/{username}")
async def get_thoughts_for_user(username : str):
    return get_thoughts(username)

@app.post("/api/v1/users")
async def register_user(user : User):
    username  = user.username
    email = user.email
    
    if get_user_by_email(email) or get_user_by_username(username):
        raise HTTPException(status_code=400, detail="A user with that username/email already exists.")
    create_user(username, email)
    return {"Account creation" : "Successful"}

@app.post("/api/v1/thoughts")
async def create_new_thought(thought : Thought):
    user_id = thought.user_id
    title = thought.title
    content = thought.content
    
    create_thought(user_id, title, content)
    return {"Thought" : "Successfully created!"}

#---log in to get access token---#
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data : OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail= "Username/password incorrect!",
                                         headers={"WWW-Authenticate":"Bearer"}) 
    access_token_expires = timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub" : user.username}, expires_delta=access_token_expires)
    return {"access_token" : access_token, "token_type" : "bearer"}

@app.get("/api/v1/me", response_model=User)
async def read_users_me(current_user : User = Depends(get_current_active_user)):
    return current_user