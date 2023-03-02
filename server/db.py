"""This file will contain all the database logic for our server module. It will leverage the Deta Base NoSQL database api."""

from datetime import datetime
import math
from typing import Union
import os
import logging
from pprint import pprint #pylint: disable=unused-import
from uuid import uuid4
from deta import Deta
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

#---DB INIT---#
DETA_KEY = os.getenv("DETA_KEY")
deta = Deta(DETA_KEY)
#---#
USERS = deta.Base("users")
THOUGHTS = deta.Base("thoughts")
KEYS = deta.Base("keys_db")


#---PW ENCRYPT INIT---#
pwd_context = CryptContext(schemes =["bcrypt"], deprecated="auto")
#---#
def gen_pw_hash(pw:str)->str:
    """Function that will use the CryptContext module to generate and return a hashed version of our password"""
    
    return pwd_context.hash(pw)

#---USER FUNCTIONS---#
def get_users() -> dict:
    """Function to return all users from our database"""
    try:
        return {user["username"]: user for user in USERS.fetch().items}
    except Exception as e:
        # Log the error or handle it appropriately
        print(f"Error fetching users: {e}")
        return {}

def get_user_by_username(username:str)->Union[dict, None]:
    """Function that returns a User object if it is in the database. If not it returns a JSON object with the 
    message no user exists for that username"""
    
    try:
        if (USERS.fetch({"username" : username}).items) == []:
            return {"Username" : "No user with username found"}
        else:
            return USERS.fetch({"username" : username}).items[0]
    except Exception as error_message:
        logging.exception(error_message)
        return None

def get_user_by_email(email:str)->Union[dict, None]:
    """Function that returns a User object if it is in the database. If not it returns a JSON object with the 
    message no user exists for that email address"""
    
    try:
        if (USERS.fetch({"email" : email}).items) == []:
            return {"Email" : "No user with email found"}
        else:
            return USERS.fetch({"email" : email}).items[0]
    except Exception as error_message:
        logging.exception(error_message)
        return None

def change_password(username, pw_to_hash):
    """Function that takes a username and a password in plaintext. It will then hash that password>
    After that it creates a dictionary and tries to match the username to users in the database. If 
    successful it overwrites the previous password hash. If not it returns a JSON message stating no 
    user could be found for the username provided."""
    
    hashed_pw = gen_pw_hash(pw_to_hash)
    update= {"hashed_pw": hashed_pw }
    
    try:
        user = get_user_by_username(username)
        user_key = user["key"]
        if not username in get_users():
            return {"Username" : "Not Found"}
        else:
            
            return USERS.update(update, user_key), f"User {username} password changed!"
    except Exception as error_message:
        logging.exception(error_message)
        return None       
    
def create_user(username:str, email:str, pw_to_hash:str)->None:
    """Function to create a new user. It takes three strings and inputs these into the new_user dictionary. The function then
    attempts to put this dictionary in the database"""

    new_user = {"username" : username,
                "key" : str(uuid4()),
                "hashed_pw" : gen_pw_hash(pw_to_hash), 
                "email" : email,
                "friends" : [],
                "disabled" : False}
    try:
        return USERS.put(new_user)
    except Exception as error_message:
        logging.exception(error_message)
        return None
    
#---FRIENDS FUNCTIONS---#    
def get_friends_by_username(username:str)->Union[dict, None]:
    """Function that will get a list of all usernames in the friends array of the user object. It will then collect all the friends
    user profile info for each friend, add it to a dictionary and then return that dictionary."""
    
    friends_list =[]
    
    try:
        friends_list = USERS.fetch({"username" : username}).items[0]["friends"]
        friends_dict = {}
        for friend in friends_list:
            user = get_user_by_username(friend)
            friends_dict[user['username']] = {"email":user['email']}
        return friends_dict    
    except Exception as error_message:
        logging.exception(error_message)
        return None
    
def add_friend(username, friend_username):
    """Function that takes a username and the username of a friend. An update dictionary is created with that friend's username. The function 
    will then check if the friend exists, if you are not trying to add yourself or if the user in question is not already a friend. If all
    these checks are passed and attempt is made to add the friend to the friends array in the database of the User object."""
    
    update= {"friends": USERS.util.append(friend_username) }
    
    try:
        user = get_user_by_username(username)
        user_key = user["key"]
        if not friend_username in get_users():
            return {"Username" : "Not Found"}
        elif username == friend_username:
            return{"Username" : "You can't add yourself as a friend!"}
        elif friend_username in user["friends"]:
            return {"Username" : "Already a friend!"}
        else:
            return USERS.update(update, user_key), f"User {friend_username} added as a friend successfully!"
    except Exception as error_message:
        logging.exception(error_message)
        return None
    

#---THOUGHTS FUNCTIONS---#
def update_rating(rating:float)->float:
    """Helper function that takes the rating float from a Thoughts object and performs a logarithmic calculation on it. The result is 
    then returned."""
    
    rating += math.log(rating+1)
    return rating

def get_thought(query_str:str)->Union[dict, str, None]:
    """Function to find a Thought by title. Might need refinement when implementing the encryption aspect."""
    try:
        thought_list=THOUGHTS.fetch().items
        for thought in thought_list:
            if query_str.lower() in thought["title"].lower():
                return thought
            else:
                return f"No thought found for the search term {query_str}"
    except Exception as error_message:
        logging.exception(error_message)
        return None

def get_thoughts(username:str)->Union[dict, None]:
    """Function to find all thoughts created by a certain user. Will return a dictionary of all the Thought objects that have the usernames username
    provided."""
    try:
        return THOUGHTS.fetch({"username" : username}).items
    except Exception as error_message:
        logging.exception(error_message)
        return None

def create_thought(username:str, title:str, content:str )->None:
    """Basic function to create a Thought. Will need refinement to handle encrypted data for the content field and probably an additional array
    to store all the versions of the encrypted symmetric key."""
    new_thought = {"username" : username,
                   "key" : str(uuid4()), 
                   "title" : title, 
                   "content" : content,
                   "rating" : 0.0,
                   "creation_date": str(datetime.utcnow())
                   }
    try:
        return THOUGHTS.put(new_thought)
    except Exception as error_message:
        logging.exception(error_message)
        return None


#---PUBLIC KEY FUNCTIONS---#
def get_public_key(username:str)->Union[bytes, None]:
    """Helper function to allow the endpoint to get a users public key from the database and use it to encrypt a symmetric key."""
    try:
        retrieved_key = KEYS.get(f"{username}")["public key"]
        new_public_key = retrieved_key.encode("utf-8")
        return new_public_key
    except Exception as error_message:
        print(error_message)
        return None


def upload_public_key(public_key:bytes, username:str)->Union[bool, None]:
    """Helper function to allow the endpoint to upload a provided public key string to the database. It will also use the get_public_key
    function to verify that the key in the database matches the original. Improvement needed on removing a public key that does not match the check
    from the database again."""
    pub_key = {"key" : username, 
               "public key" : public_key}
    try:
        KEYS.put(pub_key)
    except Exception as error_message:
        logging.exception(error_message)
        
    try:
        retrieved_key = get_public_key(username)
        print(type(retrieved_key))
        print(type(public_key))
        if public_key.encode('utf-8')==retrieved_key:
            print("Public key uploaded succesfully")
            return True
        else:
            print("Public key upload corrupted, please try again!")
            return False
    except Exception as error_message:
        logging.exception(error_message)
        return None
    
