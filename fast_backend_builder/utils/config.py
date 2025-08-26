# mypkg/config.py
USER_MODEL = None
USER_MODEL_REF = None  # dotted path string, e.g. "app.models.User"

def set_user_model(model, model_ref: str):
    global USER_MODEL, USER_MODEL_REF
    USER_MODEL = model
    USER_MODEL_REF = model_ref

def get_user_model():
    if USER_MODEL is None:
        raise RuntimeError("User model not configured. Call set_user_model(User, 'app.models.User').")
    return USER_MODEL

def get_user_model_reference() -> str:
    if USER_MODEL_REF is None:
        raise RuntimeError("User model reference not configured.")
    return USER_MODEL_REF

MODEL_PACKAGES: list[str] = []

def set_model_packages(packages: list[str]):
    global MODEL_PACKAGES
    MODEL_PACKAGES = packages

def get_model_packages() -> list[str]:
    if not MODEL_PACKAGES:
        raise RuntimeError("Model packages not set. Call set_model_packages() first.")
    return MODEL_PACKAGES