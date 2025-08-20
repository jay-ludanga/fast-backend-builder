Building The package:

python setup.py sdist bdist_wheel

install the package to your app:

pip install path/to/wheel file

generating Graphql schemas

graphql gen:crud-api <module-name> --model Model1,Model2,Model3

generating graphql schemas with attachments

graphql gen:crud-api <module-name> --model ModelName --with-attachment

for attachments you must have minio server and these .env configs:

MINIO_SERVER=ip_address:api_port
MINIO_BUCKET=backet-name
MINIO_ACCESS_KEY=minio-username
MINIO_SECRETE_KEY=minio-password
MINIO_SECURE=False

You must initialize the MinioService before using it by:

@app.on_event("startup")
async def startup_event():
    # Run the init_minio_service in the background without blocking the app startup
    asyncio.create_task(init_minio_service())

async def init_minio_service():
    minio_service = MinioService()
    try:
        await minio_service.init(
            server=config('MINIO_SERVER'),
            access_key=config('MINIO_ACCESS_KEY'),
            secret_key=config('MINIO_SECRETE_KEY'),
            bucket_name=config('MINIO_BUCKET'),
            secure=config('MINIO_SECURE', cast=bool)
        )
    except Exception as e:
        print(f"Error initializing MinIO service: {e}")

Making it async will easy your app booting process.

If you need to use the service out of generated crud apis yo do:

For uploading:

file_location, upload_error = await MinioService.get_instance().upload_file(
    file_name=f"path/to/file.extension",
    file_data=base64_decoded_file,
    content_type=attachment.file.content_type
)

For downloading:

base64_content = await MinioService.get_instance().download_file("path/to/file.extension")

For deleting:

result = MinioService.get_instance().delete_file("path/to/file.extension")

