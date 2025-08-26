
import re

def to_snake_case(name):
    """
    Converts a given string from PascalCase or CamelCase to snake_case.

    Parameters:
    - name (str): The input string in PascalCase or CamelCase format.

    Returns:
    - str: The string converted to snake_case format.

    Example:
    - Input: 'CamelCase' or 'PascalCase'
    - Output: 'camel_case' or 'pascal_case'
    """
    
    # Use a regular expression to find positions where an uppercase letter follows a lowercase letter or another uppercase letter,
    # but not at the beginning of the string (indicated by the negative lookbehind '(?<!^)').
    # The regex replaces the matched position with an underscore ('_') before the uppercase letter.
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name)
    
    # Convert the entire string to lowercase to match snake_case formatting
    return name.lower()

def to_kebab_case(name):
    """
    Converts a given string from PascalCase or CamelCase to snake_case.

    Parameters:
    - name (str): The input string in PascalCase or CamelCase format.

    Returns:
    - str: The string converted to snake_case format.

    Example:
    - Input: 'CamelCase' or 'PascalCase'
    - Output: 'camel_case' or 'pascal_case'
    """
    
    # Use a regular expression to find positions where an uppercase letter follows a lowercase letter or another uppercase letter,
    # but not at the beginning of the string (indicated by the negative lookbehind '(?<!^)').
    # The regex replaces the matched position with an underscore ('_') before the uppercase letter.
    name = re.sub(r'(?<!^)(?=[A-Z])', '-', name)
    
    # Convert the entire string to lowercase to match snake_case formatting
    return name.lower()

def to_title_case(snake_str: str) -> str:
    """
    Converts a snake_case string to Title Case.
    
    Args:
        snake_str (str): The snake_case string to convert.

    Returns:
        str: The converted string in Title Case.

    Raises:
        ValueError: If the input is not a valid snake_case string.
    """
    if not isinstance(snake_str, str):
        raise ValueError("Input must be a string.")
    
    if not snake_str:
        return ''

    # Split the string by underscores and capitalize each word
    if snake_str.find("_") != -1:
        words = snake_str.split('_')
    elif snake_str.find("-") != -1:
        words = snake_str.split('-')
    else: words = snake_str.split(' ')
    
    # Capitalize and join words into Title Case format
    title_case_str = ' '.join(word.capitalize() for word in words if word)
    
    return title_case_str

def remove_between(str, start, end, inclusive=True):
    """
    Remove all characters between 'start' and 'end', with the option to include or exclude
    the 'start' and 'end' substrings themselves.

    Parameters:
    - str (str): The input string to modify (can be multiline).
    - start (str): The substring indicating the start of the removal region.
    - end (str): The substring indicating the end of the removal region.
    - inclusive (bool): If True, remove 'start' and 'end' along with the content in between.
                        If False, keep 'start' and 'end', but remove only the content between them.

    Returns:
    - str: The modified string with the specified content removed.
    """
    
    if inclusive:
        # Pattern to match and remove everything between 'start' and 'end', including them
        pattern = re.escape(start) + ".*?" + re.escape(end)
    else:
        # Pattern to remove only the content between 'start' and 'end', keeping the substrings themselves
        pattern = re.escape(start) + "(.*?)" + re.escape(end)
    
    # Use re.sub to replace the matched pattern with an empty string or with the preserved start/end strings
    # Use re.DOTALL to ensure multi-line support
    return re.sub(pattern, '' if inclusive else start + end, str, flags=re.DOTALL)

def to_strptime_format(date_format: str) -> str:
    # Dictionary mapping placeholders without % to those with %
    format_map = {
        'Y': '%Y',  # Four-digit year
        'y': '%y',  # Two-digit year
        'm': '%m',  # Month (01-12)
        'd': '%d',  # Day of the month (01-31)
        'H': '%H',  # Hour (24-hour format, 00-23)
        'M': '%M',  # Minute (00-59)
        'S': '%S',  # Second (00-59)
    }
    
    # Replace each placeholder in the input format with the appropriate % placeholder
    for key, value in format_map.items():
        date_format = date_format.replace(key, value)
    
    return date_format

def is_valid_email(email: str) -> bool:
    """
    Validate an email address using a regular expression.
    
    Args:
        email (str): The email address to validate.
    
    Returns:
        bool: True if the email is valid, False otherwise.
    """
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

def is_valid_url(url: str) -> bool:
    """
    Validate a URL using a regular expression.
    
    Args:
        url (str): The URL to validate.
    
    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    url_regex = (
        r'^(https?|ftp):\/\/'  # Protocol (http, https, or ftp)
        r'(([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})'  # Domain name
        r'(:\d+)?'  # Optional port
        r'(\/[a-zA-Z0-9-._~:\/?#@!$&\'()*+,;=]*)?$'  # Resource path and query string
    )
    return re.match(url_regex, url) is not None

def to_shorter_name(name, max_length=31):
    """
    Shortens a worksheet name to ensure it does not exceed the specified length 
    while preserving whole words. If the first word itself exceeds the length, 
    it is truncated.

    Args:
        name (str): The original worksheet name.
        max_length (int): The maximum allowed length for the name (default is 31).

    Returns:
        str: A shortened worksheet name.
    """
    # If the name is already within the allowed length, return it as is
    if len(name) <= max_length:
        return name
    
    # Split the name into words
    words = name.split()
    result = []
    
    # Add words one by one until the total length exceeds the limit
    for word in words:
        if len(" ".join(result + [word])) <= max_length:
            result.append(word)
        else:
            break
    
    # If no words could fit and the first word is too long, truncate it
    if not result and len(words[0]) > max_length:
        return words[0][:max_length]
    
    # Join the collected words into a single string and return
    return " ".join(result)