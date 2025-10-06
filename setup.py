# fast_backend_builder/setup.py
from setuptools import setup, find_packages

setup(
    name='fast-backend-builder',
    version='0.1.3.19',
    packages=find_packages(),
    install_requires=[
        'fastapi==0.116.1',
        'tortoise-orm[asyncpg]==0.20.1',
        'pydantic==2.11.7',
        'httpx==0.28.1',
        'strawberry-graphql[fastapi]==0.278.1',
        'jinja2==3.1.6',
        'pluralize==20240519.3',
        'PyJWT==2.10.1',
        'redis==5.2.1',
        'minio==7.2.16',
        'aiofiles==24.1.0',
        'bullmq==2.15.0',
        'sentry_sdk==2.34.1',
        'cryptography==45.0.6',
        'python-decouple==3.8',
        'celery[redis]==5.5.3',
        'xlsxwriter==3.2.5',
        'fpdf2==2.8.3',
    ],
    entry_points={
        'console_scripts': [
            'graphql=fast_backend_builder.commands.graphql:main',  # maps 'graphql-gen' to 'generate_schema.py'
            'reportviews=fast_backend_builder.commands.report_views:main',  # maps 'graphql-gen' to 'generate_schema.py'
        ],
    },
    include_package_data=True,
    zip_safe=False,
    description='FastAPI Builder with Tortoise ORM support',
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author='Japhary Juma Hamisi',
    author_email='japharyjuma@gmail.com',
    url='https://github.com/jay-ludanga/fast-api-builder',
    package_data={
        # If your package has data files in a subdirectory
        'fast_backend_builder': [
            'common/templates/*',
            'crud/templates/*',
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: FastAPI",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
)
