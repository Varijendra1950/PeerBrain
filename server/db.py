from deta import Deta
from pprint import pprint
from uuid import UUID, uuid4
from dotenv import load_dotenv
import os
import json
from passlib.context import CryptContext
from datetime import datetime


#---LOCAL IMPORTS---#
from models import User, Thought

load_dotenv()

#---DB INIT---#
DETA_KEY = os.getenv("DETA_KEY")
deta = Deta(DETA_KEY)

USERS = deta.Base("users")
THOUGHTS = deta.Base("thoughts")

#---PW ENCRYPT INIT---#
pwd_context = CryptContext(schemes =["bcrypt"], deprecated="auto")

#---USER FUNCTIONS---#
def get_user_by_username(username:str)->dict:
    try:
        return USERS.fetch({"username" : username}).items  
    except Exception as e:
        print(e)
      
def get_user_by_email(email:str)->dict:
    try:
        return USERS.fetch({"email" : email}).items  
    except Exception as e:
        print(e)

def get_users()->dict:
    user_dict = {}
    for user in USERS.fetch().items:
        user_dict[user["username"]]=user
    return user_dict
        
def create_user(username:str, email:str, pw_to_hash:str)->None:
    
    new_user = {"username" : username, 
                "key" : str(uuid4()),
                "hashed_pw" : gen_pw_hash(pw_to_hash), 
                "email" : email,
                "disabled" : False}
    try:
        USERS.put(new_user)
    except Exception as e:
        print(e)

def gen_pw_hash(pw):
    return pwd_context.hash(pw)

    
#---THOUGHTS FUNCTIONS---#
def get_thoughts(username:str)->dict:
    user_id = get_user_by_username(username)[0]["key"]
    try:
        return THOUGHTS.fetch({"user_id" : user_id}).items  
    except Exception as e:
        print(e)

def create_thought(user_id:str, title:str, content:str )->None:
    new_thought = {"user_id" : user_id,
                   "key" : str(uuid4()), 
                   "title" : title, 
                   "content" : content,
                   "rating" : 0.0,
                   "creation_date": datetime.utcnow()
                   }
    try:
        THOUGHTS.put(new_thought)
    except Exception as e:
        print(e)
        
 
#create_thought("177ccd28-1194-4889-a20e-ffd159ff9557", "testtweet2", "Second try at creating a tweet, this should prove very interesting. How fun!")              
#print(get_thoughts("testuser"))
#print(get_user_by_email("tom.teck@gmail.com"))
# create_user("admin", "tom.teck@gmail.com", "test123")
# create_user("model", "tom.teck@ontexglobal.com", "test124")
# create_user("user", "tom.teck@msn.com", "test125")

#print(get_users())
