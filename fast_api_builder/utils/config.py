# mypkg/config.py
USER_MODEL = None

def set_user_model(model):
    global USER_MODEL
    USER_MODEL = model

def get_user_model():
    if USER_MODEL is None:
        raise RuntimeError("User model not configured. Call set_user_model(User).")
    return USER_MODEL