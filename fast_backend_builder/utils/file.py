# read a text file from path and return its contents
import importlib
import os


def get_file_content(filename: str):
    try:
        with open(filename, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File '{filename}' File not found.")
        return False
    return content

# Reads a file from a package
def get_package_file(package: str, filename: str):
    try:
        print(f"Reading File '{package}/{filename}'")
        with importlib.resources.open_text(package, filename) as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Template file '{package}/{filename}' File not found.")
        return False
    return content

# writes the contents to a file
def write_to_file(filename: str, content: str):
    directory_path = os.path.dirname(filename)
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        
        with open(f"{directory_path}/__init__.py", "w") as f:
            f.write("")
        
        print("Directory created successfully.")

    with open(filename, "w") as f:
        f.write(content)