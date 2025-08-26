import base64
# import imghdr
import json
import re
from typing import Type, Any, Optional, List, Dict, Union
from functools import wraps
from datetime import date, datetime

from pydantic_core import ErrorDetails

from fast_backend_builder.common.response.schemas import ErrorDetail
from fast_backend_builder.common.validation.rules import FieldRules
from fast_backend_builder.utils.error_logging import log_exception
from fast_backend_builder.utils.reflection import get_class, get_class_instance
from fast_backend_builder.utils.str_helpers import *
from fast_backend_builder.common.schemas import ModelType

class ValidationError(Exception):
    def __init__(self, message: str, errors: list = None):
        """
        Initialize the ValidationError with a message and optional errors.

        Args:
            message (str): The main error message.
            errors (list): A list of specific field errors.
        """
        super().__init__(message)  # Call the base class constructor with the message
        self.errors = errors if errors else []

    def __str__(self):
        """
        String representation of the error. This will show the message and errors.
        """
        # if self.errors:
        #     return f"{self.args[0]}: {self.errors}"
        return self.args[0]

class FieldValidator:

    def __init__(self):
        # Define the regex pattern for each country using their ISO country codes
        self.locale_patterns = {
            'TZ': r"^(?:\+255|0)(2|[6-7][1-9]\d{7})$",  # Tanzania
            'KE': r"^(?:\+254|0)(2|[6-7][0-9]\d{7})$",  # Kenya
            'UG': r"^(?:\+256|0)(2|[6-7][0-9]\d{7})$",  # Uganda
            'BI': r"^(?:\+257|0)(2|[6-7][1-9]\d{7})$",  # Burundi
            'RW': r"^(?:\+250|0)(2|[6-7][1-9]\d{7})$",  # Rwanda
            # You can add more country patterns here
        }

    async def validate_field(self, field_rule: FieldRules, data: Optional[dict] = None):
        field = field_rule.field
        value = self.field_value(field, data)
        field_name = to_title_case(field)

        for rule, param in field_rule.rules:
            # Nullable validation
            if rule == 'nullable' and (value is None or value == ''):
                # If value is null or empty and nullable is set, skip further validation
                return

            # Required validation
            if rule == 'required' and (value is None or value == ''):
                raise ValidationError(f"Field '{field_name}' is required")

            # Required If validation
            if rule == 'required_if':
                comparison_field, comparison_value, messages = param

                # Handle wildcard notation for comparison_field
                if '*' in comparison_field:
                    base_field = comparison_field.split('.')[0]  # Get base field name (e.g., "reasons")
                    if not (base_field in data and isinstance(data[base_field], list)):
                        raise ValidationError(f"{field_name} must be an array")

                    # Check if any element in the list matches the comparison_value
                    if any(item == comparison_value for item in data[base_field]):
                        if value is None or value == '':
                            raise ValidationError(f"{field_name} is required when {base_field} contains {comparison_value}")
                else:
                    # If no wildcard, use direct comparison
                    if data.get(comparison_field) == comparison_value and (value is None or value == ''):
                        raise ValidationError(messages if messages else f"{field_name} is required when {comparison_field} is {comparison_value}")

            # Required Unless validation
            if rule == 'required_unless':
                comparison_field, comparison_value = param
                if data.get(comparison_field) != comparison_value and (value is None or value == ''):
                    raise ValidationError(f"{field_name} is required unless {comparison_field} is {comparison_value}")


            # Min length validation
            if rule == ('min'):
                min_value = param
                if isinstance(value, str) and len(value) < min_value:
                    raise ValidationError(f"{field_name} must be at least {min_value} characters long")
                elif isinstance(value, (int, float)) and value < min_value:
                    raise ValidationError(f"{field_name} must be at least {min_value}")

            # Max length validation
            if rule == ('max'):
                max_value = param
                if isinstance(value, str) and len(value) > max_value:
                    raise ValidationError(f"{field_name} must be less than {max_value} characters long")
                elif isinstance(value, (int, float)) and value > max_value:
                    raise ValidationError(f"{field_name} must be less than {max_value}")

            # Noun validation
            if rule == 'noun':
                if not self.is_valid_noun(value):
                    raise ValidationError(f"{field_name} must be a valid noun")

            # Noun validation
            if rule == 'full_name':
                if not self.is_valid_full_name(value):
                    raise ValidationError(f"{field_name} must be a valid full name with names separated by spaces")

            # Birth date validation
            if rule == ('birth_date'):
                age_range, date_format = param

                try:
                    # Convert birth date to a date object using the provided or default date format
                    birth_date = datetime.strptime(value, to_strptime_format(date_format)).date()

                    # Calculate current age
                    today = date.today()
                    current_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

                    # Handling age validation cases (single age, age range, or minimum age)
                    if '-' in age_range:
                        # Case for age range (e.g., '18-19')
                        min_age, max_age = map(int, age_range.split('-'))
                        if not (min_age <= current_age <= max_age):
                            raise ValidationError(f"{field_name} must indicate a person aged between {min_age} and {max_age} years old")

                    elif age_range.endswith('+'):
                        # Case for minimum age (e.g., '18+')
                        min_age = int(age_range[:-1])
                        if current_age < min_age:
                            raise ValidationError(f"{field_name} must indicate a person who is at least {min_age} years old")

                    else:
                        # Case for exact age (e.g., '18')
                        exact_age = int(age_range)
                        if current_age != exact_age:
                            raise ValidationError(f"{field_name} must indicate a person who is exactly {exact_age} years old")

                except ValueError:
                    raise ValidationError(f"{field_name} must follow the format {date_format}")

            # Address validation
            if rule == 'address':
                if not self.is_valid_address(value):
                    raise ValidationError(f"{field_name} must be a valid address")

            # Phone validation
            if rule == 'phone':
                locales = param
                if isinstance(locales, str):
                    locales = locales.replace(' ', '').split(',')
                if not self.is_valid_phone(value, locales):
                    if locales and isinstance(locales, list):
                        locales = f"in {', '.join(locales)}"
                    raise ValidationError(f"{field_name} must be a valid phone number {locales}")

            # Confirmed validation
            if rule == 'password':
                if not self.is_strong_password(value):
                    raise ValidationError(f"{field_name} must contain letters, numbers, and special characters")

            # Confirmed validation
            if rule == 'confirmed':
                comparison_field = f"{field}_confirmation"
                if data.get(comparison_field) != value:
                    raise ValidationError(f"{field_name} confirmation does not match {comparison_field}")

            # Email validation
            if rule == 'email' and (not isinstance(value, str) or not is_valid_email(value)):
                raise ValidationError(f"{field_name} must be a valid email")

            # URL validation
            if rule == 'url' and (not isinstance(value, str) or not is_valid_url(value)):
                raise ValidationError(f"{field_name} must be a valid url")

            # Integer validation
            if rule == 'integer' and not isinstance(value, int):
                raise ValidationError(f"{field_name} must be an integer")

            # Decimal validation
            if rule == 'decimal':
                min_decimal_places, max_decimal_places = param
                if not isinstance(value, float):
                    raise ValidationError(f"{field_name} must be a decimal number")
                if len(str(value).split('.')[1]) < min_decimal_places:
                    raise ValidationError(f"{field_name} must have at least {min_decimal_places} decimal places")
                if max_decimal_places and len(str(value).split('.')[1]) > max_decimal_places:
                    raise ValidationError(f"{field_name} must have at most {max_decimal_places} decimal places")

            # Digits validation
            if rule == 'digits':
                digit_length = param
                if not isinstance(value, int) or len(str(value)) != digit_length:
                    raise ValidationError(f"{field_name} must be exactly {digit_length} digits")

            # Digits Between validation
            if rule == 'digits_between':
                min_digits, max_digits = param
                if not (min_digits <= len(str(value)) <= max_digits):
                    raise ValidationError(f"{field_name} must be between {min_digits} and {max_digits} digits")

            # Numeric validation
            if rule == 'numeric' and not isinstance(value, (int, float)):
                raise ValidationError(f"{field_name} must be a numeric value")

            # Boolean validation
            if rule == 'boolean' and not isinstance(value, bool):
                raise ValidationError(f"{field_name} must be a boolean")

            # Unique validation (placeholder)
            if rule == ('unique'):
                # TODO: Add implementation of custom column exclude
                model, exclude_column, exclude_values = param
                if model:
                    query = model.filter(**{field: value})
                    try:
                        id = data['id']
                        query = query.exclude(**{f"id": id})
                    except:
                        pass
                    if exclude_values:
                        query = query.exclude(**{f"{exclude_column}__in": exclude_values})
                    if await query.exists():
                        raise ValidationError(f"{model.Meta.verbose_name} with '{field}={value}' already exist")

            # Unique with validation (placeholder)
            if rule == ('unique_with'):
                model, other_field, exclude_column, exclude_values = param
                try:
                    other_value = data[other_field]
                except Exception:
                    raise ValidationError(f"Field '{to_title_case(other_field)}' is required")
                if model:
                    query = model.filter(**{field: value, other_field: other_value})
                    try:
                        id = data['id']
                        query = query.exclude(**{f"id": id})
                    except:
                        pass
                    if exclude_values:
                        query = query.exclude(**{f"{exclude_column}__in": exclude_values})
                    if await query.exists():
                        raise ValidationError(f"{model.Meta.verbose_name} with '{field_name}={value}' and this '{to_title_case(other_field)}' already exist")

            # Exists validation (placeholder)
            if rule == 'exists_as':
                model, as_column, exclude_column, exclude_values = param
                if model:
                    query = model.filter(**{as_column: value})
                    try:
                        id = data['id']
                        query = query.exclude(**{f"id": id})
                    except:
                        pass
                    if exclude_values:
                        query = query.exclude(**{f"{exclude_column}__in": exclude_values})
                    if not await query.exists():
                        raise ValidationError(f"{model.Meta.verbose_name} with '{as_column}={value}' does not exist")

            # Regex validation
            if rule == ('regex'):
                pattern = param
                if not re.match(pattern, value):
                    raise ValidationError(f"{field_name} does not match the required pattern: {pattern}")

            # Inclusion validation
            if rule == ('in'):
                options = param
                if isinstance(options, str):
                    options = options.replace(' ', '').split(',')
                if value not in options:
                    raise ValidationError(f"{field_name} must be one of: {', '.join(options)}")

            # Enum validation
            if rule == ('enum'):
                enum_class = param
                try:
                    enum_class(value)  # Try to instantiate with the value
                except ValueError:
                    raise ValidationError(f"{enum_class.__qualname__} with '{field}={value}' does not exist")

            # Date range validation
            if rule == ('date_range'):
                date_field, current_time = param
                if not self.is_within_date_range(data.get(date_field), value, current_time):
                    raise ValidationError(f"{field_name} must be within the specified date range")

            # Date Equals validation
            if rule == ('date_equals:'):
                comparison_date = rule.split(':')[1]
                if not self.is_valid_date(value):
                    raise ValidationError("Invalid date format")
                if value != comparison_date:
                    raise ValidationError(f"{field_name} must equal {comparison_date}")

            # Declined validation
            if rule == 'declined' and value != 'declined':
                raise ValidationError(f"{field_name} must be declined")

            # Declined If validation
            if rule == ('declined_if:'):
                comparison_field, comparison_value = rule.split(':')[1].split(',')
                if data.get(comparison_field) == comparison_value and value != 'declined':
                    raise ValidationError(f"{field_name} must be declined")

            # Different validation
            if rule == ('different:'):
                comparison_field = rule.split(':')[1]
                if value == data.get(comparison_field):
                    raise ValidationError(f"{field_name} must be different from {comparison_field}")

            # Distinct validation
            if rule == 'distinct':
                if isinstance(value, list) and len(value) != len(set(value)):
                    raise ValidationError(f"{field_name} must have distinct values")

            # Doesnt Start With validation
            if rule == ('doesnt_start_with:'):
                prefix = rule.split(':')[1]
                if isinstance(value, str) and value.startswith(prefix):
                    raise ValidationError(f"{field_name} must not start with {prefix}")

            # Doesnt End With validation
            if rule == ('doesnt_end_with:'):
                suffix = rule.split(':')[1]
                if isinstance(value, str) and value.endswith(suffix):
                    raise ValidationError(f"{field_name} must not end with {suffix}")

            # Extensions validation
            if rule == ('extensions:'):
                valid_extensions = rule.split(':')[1].split(',')
                if not any(value.endswith(ext) for ext in valid_extensions):
                    raise ValidationError(f"{field_name} must have one of the following extensions: {', '.join(valid_extensions)}")

            # Filled validation
            if rule == 'filled' and (value is None or value == ''):
                raise ValidationError(f"{field_name} must be filled")

            # Hex Color validation
            if rule == 'hex_color' and not re.match(r'^#([0-9a-fA-F]{3}){1,2}$', value):
                raise ValidationError(f"{field_name} must be a valid hex color")

            # Image validation
            if rule == 'base64':
                file_type, max_size = param
                if isinstance(value, str) and self.is_valid_in_regex(r'^[A-Za-z0-9+/]+={0,2}$', value.strip()):
                    try:
                        decoded_data = base64.b64decode(value)
                    except Exception:
                        raise ValidationError(f"{field_name} must be a valid base64 string")

                    if file_type == 'image':
                        image_type = imghdr.what(None, decoded_data)

                        if not image_type:
                            raise ValidationError(f"{field_name} must be a valid image file")

                    # Calculate size in bytes
                    if max_size:
                        size_in_bytes = len(decoded_data)
                        max_size_c = max_size.upper()

                        # Convert bytes to KB or MB
                        if max_size_c.find('KB') != -1:
                            size_in_kb = size_in_bytes / 1024
                            if size_in_kb > float(max_size_c.split('K')[0].strip()):
                                raise ValueError(f"{field_name} size must not be greeter than {max_size}")

                        if max_size_c.find('MB') != -1:
                            size_in_mb = size_in_bytes / (1024 * 1024)
                            if size_in_mb > float(max_size_c.split('M')[0].strip()):
                                raise ValueError(f"File size exceeds the maximum allowed size of {max_size}")

                else:
                    raise ValidationError(f"{field_name} must be a valid base64 string")

            # Lowercase validation
            if rule == 'lowercase':
                if not isinstance(value, str):
                    raise ValidationError(f"{field_name} must be a lowercase string")
                elif isinstance(value, str) and value != value.lower():
                    raise ValidationError(f"{field_name} must be lowercase")

            # Uppercase validation
            if rule == 'uppercase':
                if not isinstance(value, str):
                    raise ValidationError(f"{field_name} must be an uppercase string")
                elif isinstance(value, str) and value != value.upper():
                    raise ValidationError(f"{field_name} must be uppercase")

            # MIME Type validation
            if rule == ('mime_type:'):
                mime_type = rule.split(':')[1]
                # Check the MIME type logic here (depends on the file type handling)

            # UUID validation
            if rule == 'uuid' and not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value):
                raise ValidationError(f"{field_name} must be a valid UUID")

            # ULID validation
            if rule == 'ulid' and not re.match(r'^[0-9A-HJKM-NPRT-Z]{26}$', value):
                raise ValidationError(f"{field_name} must be a valid ULID")

            # Prohibited validation
            if rule == 'prohibited' and value is not None:
                raise ValidationError(f"{field_name} is prohibited")

            # Regular Expression validation
            if rule == ('regex:'):
                pattern = rule.split(':')[1]
                if not re.match(pattern, value):
                    raise ValidationError(f"{field_name} does not match the required pattern: {pattern}")

            # Prohibited If validation
            if rule == ('prohibited_if:'):
                comparison_field, comparison_value = rule.split(':')[1].split(',')
                if data.get(comparison_field) == comparison_value and value is not None:
                    raise ValidationError(f"{field_name} is prohibited")

            # Prohibited Unless validation
            if rule == ('prohibited_unless:'):
                comparison_field, comparison_value = rule.split(':')[1].split(',')
                if data.get(comparison_field) != comparison_value and value is not None:
                    raise ValidationError(f"{field_name} is prohibited")

            # Same validation
            if rule == ('same:'):
                comparison_field = rule.split(':')[1]
                if value != data.get(comparison_field):
                    raise ValidationError(f"{field_name} must be the same as {comparison_field}")

            # Timezone validation
            if rule == ('timezone:'):
                timezone = rule.split(':')[1]
                # Add logic to validate timezone

            # Accepted validation
            if rule == 'accepted' and value not in ['yes', '1', True]:
                raise ValidationError(f"{field_name} must be accepted")

            # Active URL validation
            if rule == 'active_url' and not self.is_valid_url(value):
                raise ValidationError(f"{field_name} must be a valid URL")

            # After validation
            if rule == ('after:'):
                comparison_date = rule.split(':')[1]
                if not self.is_valid_date(value):
                    raise ValidationError("Invalid date format")
                if not self.is_after(value, comparison_date):
                    raise ValidationError(f"{field_name} must be after {comparison_date}")

            # After Or Equal validation
            if rule == ('after_or_equal:'):
                comparison_date = rule.split(':')[1]
                if not self.is_valid_date(value):
                    raise ValidationError("Invalid date format")
                if not self.is_after_or_equal(value, comparison_date):
                    raise ValidationError(f"{field_name} must be after or equal to {comparison_date}")

            # Alpha validation
            if rule == 'alpha':
                if not isinstance(value, str):
                    raise ValidationError(f"{field_name} must be a string containing only alphabetic characters")
                elif isinstance(value, str) and not value.isalpha():
                    raise ValidationError(f"{field_name} must be alphabetic")

            # Alpha Dash validation
            if rule == 'alpha_dash' and not re.match(r'^[A-Za-z0-9_-]+$', value):
                raise ValidationError(f"{field_name} must be alphabetic and may contain dashes or underscores")

            # Alpha Numeric validation
            if rule == 'alpha_numeric' and not value.isalnum():
                raise ValidationError(f"{field_name} must be alphanumeric")

            if rule == 'array':
                expected_type, min_length = param

                # Check if value is a list
                if not isinstance(value, list):
                    raise ValidationError(f"{field_name} must be an array")

                # Check if the array has the minimum required length
                if len(value) < min_length:
                    raise ValidationError(f"{field_name} must contain at least {min_length} elements")

                # Check if each element in the array is of the expected type
                if expected_type:
                    for element in value:
                        if not isinstance(element, expected_type):
                            raise ValidationError(
                                f"Each element in {field_name} must be of type {expected_type.__name__}"
                            )

            # Ascii validation
            if rule == 'ascii' and not all(ord(char) < 128 for char in value):
                raise ValidationError(f"{field_name} must contain only ASCII characters")

            # Bail validation (stop on first validation failure)
            if rule == 'bail' and hasattr(FieldValidator, 'has_failed'):
                raise ValidationError("Validation failed, stopping further checks")

            # Before validation
            if rule == ('before:'):
                comparison_date = rule.split(':')[1]
                if not self.is_valid_date(value):
                    raise ValidationError("Invalid date format")
                if not self.is_before(value, comparison_date):
                    raise ValidationError(f"{field_name} must be before {comparison_date}")

            # Before Or Equal validation
            if rule == ('before_or_equal:'):
                comparison_date = rule.split(':')[1]
                if not self.is_valid_date(value):
                    raise ValidationError("Invalid date format")
                if not self.is_before_or_equal(value, comparison_date):
                    raise ValidationError(f"{field_name} must be before or equal to {comparison_date}")

            # Between validation
            if rule == ('between:'):
                min_value, max_value = map(int, rule.split(':')[1].split(','))
                if not (min_value <= value <= max_value):
                    raise ValidationError(f"{field_name} must be between {min_value} and {max_value}")

            # Boolean validation
            if rule == 'boolean' and value not in [True, False, 1, 0]:
                raise ValidationError(f"{field_name} must be a boolean")

            # Contains validation
            if rule == ('contains:'):
                required_value = rule.split(':')[1]
                if isinstance(value, list) and required_value not in value:
                    raise ValidationError(f"{field_name} must contain {required_value}")

            # Date validation
            if rule == ('date'):
                info = rule.split(":")
                format = 'Y-m-d'
                if len(info) == 2:
                    format = info[1]
                if not isinstance(value, str) or not self.is_valid_date(value, format):
                    raise ValidationError(f"{field_name} must be a valid date in format {format}")

            # Date Format validation
            if rule == ('date_format:'):
                format_string = rule.split(':')[1]
                if not self.is_valid_date_format(value, to_strptime_format(format_string)):
                    raise ValidationError(f"{field_name} must match the date format {format_string}")

            # Dimensions validation (Image Files)
            # Placeholder for image dimensions validation

            # Not In validation
            if rule == ('not_in:'):
                invalid_values = rule.split(':')[1].split(',')
                if value in invalid_values:
                    raise ValidationError(f"{field_name} must not be one of: {', '.join(invalid_values)}")

            # IP Address validation
            if rule == 'ip_address' and not self.is_valid_ip(value):
                raise ValidationError(f"{field_name} must be a valid IP address")

            # JSON validation
            if rule == 'json':
                try:
                    json.loads(value)
                except ValueError:
                    raise ValidationError(f"{field_name} must be a valid JSON string")

            # Less Than validation
            if rule == ('less_than:'):
                comparison_value = float(rule.split(':')[1])
                if not isinstance(value, (int, float)) or value >= comparison_value:
                    raise ValidationError(f"{field_name} must be less than {comparison_value}")

            # Less Than Or Equal validation
            if rule == ('less_than_or_equal:'):
                comparison_value = float(rule.split(':')[1])
                if not isinstance(value, (int, float)) or value > comparison_value:
                    raise ValidationError(f"{field_name} must be less than or equal to {comparison_value}")

            # MAC Address validation
            if rule == 'mac_address' and not re.match(r'^[0-9a-fA-F]{2}([:-])[0-9a-fA-F]{2}\1[0-9a-fA-F]{2}\1[0-9a-fA-F]{2}\1[0-9a-fA-F]{2}$', value):
                raise ValidationError(f"{field_name} must be a valid MAC address")

            # Unique validation (Database)
            # Placeholder for uniqueness check in the database

            # MIME Types validation
            if rule == ('mime_types:'):
                valid_mime_types = rule.split(':')[1].split(',')
                # Check MIME type logic here (depends on the file type handling)

            # Not Regex validation
            if rule == ('not_regex:'):
                pattern = rule.split(':')[1]
                if re.match(pattern, value):
                    raise ValidationError(f"{field_name} must not match the pattern: {pattern}")

            # Present validation
            # Placeholder for checking if a field is present (this can be context dependent)

            # Prohibits validation
            # Placeholder for prohibiting specific values

            # Size validation
            if rule == ('size:'):
                size_value = int(rule.split(':')[1])
                if len(value) != size_value:
                    raise ValidationError(f"{field_name} must be of size {size_value}")

            # Starts With validation
            if rule == ('starts_with:'):
                prefix = rule.split(':')[1]
                if isinstance(value, str) and not value.startswith(prefix):
                    raise ValidationError(f"{field_name} must start with {prefix}")

            # String validation
            if rule == 'string' and not isinstance(value, str):
                raise ValidationError(f"{field_name} must be a string")

            # Custom validation
            if rule == ('custom:'):
                custom_function = rule.split(':')[1]
                # Call the custom validation function here

            # Sometimes validation
            # Note: "sometimes" is usually a no-op, so it doesn't require explicit handling here


            # List validation (for arrays)
            if rule == 'list' and not isinstance(value, list):
                raise ValidationError(f"{field_name} must be a list")

    def is_valid_in_regex(self, pattern, value):
        return bool(re.match(pattern, value))

    def is_valid_phone(self, phone_number, locales = None):
        if locales and isinstance(locales, list):
            for locale in locales:
                pattern = self.locale_patterns.get(locale)
                return self.is_valid_in_regex(pattern, phone_number)

        return self.is_valid_in_regex(r"^(\+?\d{1,4})?((?:[0-9] ?){6,14}[0-9])$", phone_number)

    def is_valid_noun(self, value):
        return self.is_valid_in_regex(r"^[A-Za-z\s'-]{2,50}$", value)

    def is_valid_full_name(self, value):
        return self.is_valid_in_regex(r"^[A-Za-z]+(?:\s[A-Za-z]+){1,}$", value)

    def is_valid_address(self, value):
        return self.is_valid_in_regex(r"^[A-Za-z0-9\s,.-]{5,100}$", value)

    def is_strong_password(self, password):
        return self.is_valid_in_regex(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*\W)[A-Za-z\d\W]{8,}$", password)

    def is_valid_date(self, date_string: str, format: str = 'Y-m-d') -> bool:
        """Check if the string is a valid date format (YYYY-MM-DD)."""
        try:
            datetime.strptime(date_string, to_strptime_format(format))
            return True
        except ValueError:
            return False

    def is_within_date_range(self, start_date: str, end_date: str, current_time: str) -> bool:
        """Check if a date is within a specified range."""
        if not self.is_valid_date(start_date) or not self.is_valid_date(end_date):
            return False

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        current = datetime.strptime(current_time, '%Y-%m-%d')
        return start <= current <= end

    def is_valid_url(self, url):
        # Implement URL validation logic
        return True

    def is_after(self, date_str, comparison_date_str):
        # Implement logic to check if date_str is after comparison_date_str
        return True

    def is_after_or_equal(self, date_str, comparison_date_str):
        # Implement logic to check if date_str is after or equal to comparison_date_str
        return True

    def is_before(self, date_str, comparison_date_str):
        # Implement logic to check if date_str is before comparison_date_str
        return True

    def is_before_or_equal(self, date_str, comparison_date_str):
        # Implement logic to check if date_str is before or equal to comparison_date_str
        return True

    def is_valid_ip(self, ip):
        # Implement IP address validation logic
        return True

    def is_valid_date_format(self, date_str, format_string):
        # Implement date format validation logic
        return True

    async def is_unique(self, model: Type[ModelType], field, value, except_ids):
        raise ValueError(str(model))

    def field_value(self, field, data):
        """
        Retrieve the value from nested structures using dot-separated field names.

        Args:
            field (str): The dot-separated path of the field to retrieve.
            data (dict | list | object): The dictionary, list, or object from which to retrieve the value.

        Returns:
            The value at the specified field path, or None if not found.
        """
        keys = field.split('.')  # Split the field into keys
        current = data           # Start with the provided data

        for key in keys:
            if isinstance(current, dict):  # If current is a dictionary
                if key in current:
                    current = current[key]  # Move to the next level
                else:
                    return None  # Key not found
            elif isinstance(current, list):  # If current is a list
                try:
                    index = int(key)  # Try to convert key to an index
                    current = current[index]  # Move to the indexed element
                except (ValueError, IndexError):
                    return None  # If conversion fails or index is out of bounds
            elif hasattr(current, key):  # If current is an object
                current = getattr(current, key)  # Move to the attribute
            else:
                return None  # Current is neither dict, list, nor an object with the attribute, so return None

        return current  # Return the final value if found

    async def validate(self, data: dict, all_rules: list[FieldRules]):
        errors = []
        for field_rule in all_rules:
            field = field_rule.field

            if self.field_value(field, data):
                try:
                    await self.validate_field(field_rule, data)
                except ValidationError as ve:
                    errors.append(ErrorDetail(field, str(ve)))

            elif any(rule == "required" for rule, param in field_rule.rules):
                errors.append(ErrorDetail(field, f"Field '{to_title_case(field)}' is required"))

            for rule, param in field_rule.rules:
                if rule == "required_if":
                    value = self.field_value(field, data)
                    comparison_field, comparison_value, messages = param

                    if '*' in comparison_field:
                        base_field = comparison_field.split('.')[0]  # Get base field name (e.g., "reasons")
                        if not (base_field in data and isinstance(data[base_field], list)):
                            errors.append(ErrorDetail(field, f"{to_title_case(field)} must be an array"))

                        # Check if any element in the list matches the comparison_value
                        if any(item == comparison_value for item in data[base_field]):
                            if value is None or value == '':
                                errors.append(ErrorDetail(field, f"{to_title_case(field)} is required when {base_field} contains {comparison_value}"))
                    else:
                        # If no wildcard, use direct comparison
                        if data.get(comparison_field) == comparison_value and (value is None or value == ''):
                            errors.append(ErrorDetail(field, messages if messages else f"{to_title_case(field)} is required when {comparison_field} is {comparison_value}"))

                if rule == 'required_unless':
                    comparison_field, comparison_value = param
                    if data.get(comparison_field) != comparison_value and (value is None or value == ''):
                        errors.append(ErrorDetail(field, f"{to_title_case(field)} is required unless {to_title_case(comparison_field)} is {comparison_value}"))

        if len(errors):
            raise ValidationError("Validation Error", errors=errors)