# 🚀 Setting Up a Custom User Model in FastAPI with Tortoise ORM + FastAPI-Builder

This guide explains how to create a package module for your **User model**, extend it from `AbstractUser`, configure it in Tortoise ORM, and generate GraphQL + migrations.

---

## 📂 Project Structure

```bash
myapp
  ├── mymodel_package
  │   ├── __init__.py
  │   └── models
  │       └── user.py
  ├── config
  │   ├── __init__.py
  │   └── tortoise.py
  ├── main.py
  └── ...
```

👤 1. Create Your Custom User Model

Inside mymodel_package/models/user.py:
```python
from fast_api_builder.models.base_models import AbstractUser

class User(AbstractUser):
    """Custom application user model extending AbstractUser."""
    pass
```

⚙️ 2. Set Your User Model in main.py

At the top of your main.py (before any model imports):
```python
from fast_api_builder.utils.config import set_user_model
from mymodel_package.models.user import User

# Register the User model so fast_api_builder can resolve it
set_user_model(User, "models.User")
```

🗄️ 3. Create Tortoise ORM Config

Inside config/tortoise.py:
```python
from decouple import config

db_url = f"postgres://{config('DB_USER')}:{config('DB_PASSWORD')}@{config('DB_HOST')}:{config('DB_PORT')}/{config('DB_NAME')}"

TORTOISE_ORM = {
    "connections": {"default": db_url},
    "apps": {
        "models": {
            "models": [
                "fast_api_builder.models",   # built-in models
                "mymodel_package.models",    # your custom models
                "aerich.models",             # migration tracking
            ],
            "default_connection": "default",
        },
    },
    "use_tz": True,  # Enable timezone-aware datetimes
    "timezone": "Africa/Dar_es_Salaam",  # Set to EAT (Dar es Salaam)
}
```

🔧 4. Generate CRUD APIs via GraphQL

Run the following to scaffold GraphQL CRUD APIs:
```bash
# For your custom User model
graphql gen:crud-api user_management --module-package=mymodel_package.models --model User

# For fast_api_builder built-in models
graphql gen:crud-api user_management --module-package=fast_api_builder.models --model Group,Permission,Headship,Workflow,WorkflowStep,Transition,Evaluation
```

📦 5. Initialize Aerich (DB migrations)
```bash
# Initialize Aerich with your Tortoise ORM config
aerich init -t config.tortoise.TORTOISE_ORM

# Create initial migration & database tables
aerich init-db
```