from multiprocessing.spawn import import_main_path
import random
import string
from uuid import uuid4

import fastapi
import passlib.hash as _hash
import sqlalchemy.orm as orm
from authlib.integrations.starlette_client import OAuth
from bigfastapi.auth_api import create_access_token
from bigfastapi.db.database import get_db
from bigfastapi.models.organization_models import Organization
from bigfastapi.utils import settings
from fastapi import APIRouter, HTTPException, Request, status
from models.models import UserCustom
from starlette.config import Config
from google.oauth2 import id_token
from google.auth.transport import requests

app = APIRouter()


# OAuth settings
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
if GOOGLE_CLIENT_ID is None or GOOGLE_CLIENT_SECRET is None:
    raise BaseException("Missing env variables")

# Set up OAuth
config_data = {
    "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
}
starlette_config = Config(environ=config_data)
oauth = OAuth(starlette_config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Set up the middleware to read the request session
SECRET_KEY = settings.JWT_SECRET
BASE_URL = settings.BASE_URL

# Error
CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Google oauth error",
    headers={"WWW-Authenticate": "Bearer"},
)


@app.get("/google/token")
async def auth(request: Request, token:str, db: orm.Session = fastapi.Depends(get_db)):

    try:
        user_data = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)

        check_user = valid_email_from_db(user_data["email"], db)
    
    except Exception as e:
        raise CREDENTIALS_EXCEPTION

    if check_user:
        user_id = str(check_user.id)
        access_token = await create_access_token(data={"user_id": check_user.id}, db=db)
        response = {
            "access_token": access_token,
            "user_id": user_id,
        }
        return response

    S = 10
    ran = "".join(random.choices(string.ascii_uppercase + string.digits, k=S))
    n = str(ran)

    user_obj = UserCustom(
        id=uuid4().hex,
        email=user_data.email,
        password=_hash.sha256_crypt.hash(n),
        first_name=user_data.given_name,
        last_name=user_data.family_name,
        phone_number=n,
        is_active=True,
        is_verified=True,
        country_code="",
        is_deleted=False,
        country="",
        state="",
        google_id="",
        google_image=user_data.picture,
        image=user_data.picture,
        device_id="",
    )

    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)

    token = access_token["id_token"]
    response = {
        "access_token": token,
        "user_id": user_id,
    }
    return response


def valid_email_from_db(email, db: orm.Session = fastapi.Depends(get_db)):
    found_user = db.query(UserCustom).filter(UserCustom.email == email).first()
    return found_user