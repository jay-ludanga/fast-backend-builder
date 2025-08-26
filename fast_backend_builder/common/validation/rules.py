from typing import Any, Type
from tortoise import Model


class FieldRules:
    def __init__(self, field):
        self.field = field
        self.rules = []  # Store validation rules

    # Nullable validation
    # Validates that the value can be None or empty, but if present, it must pass other rules.
    def nullable(self):
        self.rules.append(('nullable', None))
        return self

    # Add 'required' rule
    def required(self):
        self.rules.append(('required', None))
        return self
    
    # Required If validation
    # Validates that the field is required if the value of another field matches the specified comparison value.
    # Arguments:
    # - comparison_field: The field to compare with.
    # - comparison_value: The value that triggers the requirement.
    def required_if(self, comparison_field, comparison_value, messages = None):
        self.rules.append(('required_if', (comparison_field, comparison_value, messages)))
        return self

    # Required Unless validation
    # Validates that the field is required unless the value of another field matches the specified comparison value.
    # Arguments:
    # - comparison_field: The field to compare with.
    # - comparison_value: The value that bypasses the requirement.
    def required_unless(self, comparison_field, comparison_value):
        self.rules.append(('required_unless', (comparison_field, comparison_value)))
        return self
    
    # Add 'min' length or value rule
    def min(self, min_value):
        self.rules.append(('min', min_value))
        return self
    
    # Add 'max' length or value rule
    def max(self, max_value):
        self.rules.append(('max', max_value))
        return self
    
    # Add 'noun' rule
    def noun(self):
        self.rules.append(('noun'))
        return self
    
    # Add 'full_name' rule
    def full_name(self):
        self.rules.append(('full_name', None))
        return self
    
    # Add 'birth_date' rule
    def birth_date(self, age_range, date_format='Y-m-d'):
        self.rules.append(('birth_date', (age_range, date_format)))
        return self
    
    # Add 'address' rule
    def address(self, locales=None):
        self.rules.append(('address', locales))
        return self
    
    # Add 'phone' validation rule with optional locales
    def phone(self, locales=None):
        self.rules.append(('phone', locales))
        return self
    
    # Add 'password' validation rule
    # Validates if the password contains letters, numbers, and special characters
    def password(self):
        self.rules.append(('password', None))
        return self
    
    # Add 'confirmed' validation rule
    # Ensures that the value matches the confirmation field (e.g., password_confirmation)
    def confirmed(self):
        self.rules.append(('confirmed', None))
        return self
    
    # Add 'email' validation rule
    # Validates if the value is a valid email address format
    def email(self):
        self.rules.append(('email', None))
        return self
    
    # Add 'url' validation rule
    # Validates if the value is a valid URL format
    def url(self):
        self.rules.append(('url', None))
        return self
    
    # Add 'integer' validation rule
    # Ensures the value is an integer
    def integer(self):
        self.rules.append(('integer', None))
        return self
    
    # Decimal validation
    # Validates that the value must be a decimal number with a specific number of decimal places.
    # Argument:
    # - min_decimal_places: Minimum number of decimal places allowed for the decimal value.
    # - max_decimal_places: Maximum number of decimal places allowed for the decimal value.
    def decimal(self, min_decimal_places: int = 2, max_decimal_places: int = None):
        self.rules.append(('decimal', (min_decimal_places, max_decimal_places)))
        return self

    # Digits validation
    # Validates that the value must have an exact number of digits.
    # Argument:
    # - digit_length: The exact number of digits the value must have.
    def digits(self, digit_length):
        self.rules.append(('digits', digit_length))
        return self

    # Digits Between validation
    # Validates that the value must have a number of digits between the specified minimum and maximum.
    # Arguments:
    # - min_digits: The minimum number of digits allowed.
    # - max_digits: The maximum number of digits allowed.
    def digits_between(self, min_digits, max_digits):
        self.rules.append(('digits_between', (min_digits,max_digits)))
        return self
    
    # Add 'numeric' validation rule
    # Validates that the value is either an integer or a float, ensuring it's a numeric value
    def numeric(self):
        self.rules.append(('numeric', None))
        return self
    
    # Add 'boolean' validation rule
    # Validates that the value is of type bool, ensuring it's a boolean value (True or False)
    def boolean(self):
        self.rules.append(('boolean', None))
        return self
    
    # Add 'unique' rule
    def unique(self, model: Model, exclude_column = 'id', exclude_values: list = []):
        self.rules.append(('unique', (model, exclude_column, exclude_values)))
        return self
    
    # Add 'unique_with' rule
    # Validates that a record is unique in the specified model base on two fields.
    # Expects the model name to be provided in the rule as 'exists:ModelName'.
    def unique_with(self, model: Model, other_field, exclude_column = 'id', exclude_values: list = []):
        self.rules.append(('unique_with', (model, other_field, exclude_column, exclude_values)))
        return self
    
    # Add 'exists_as' validation rule
    # Validates that a record exists in the specified model based on a specified column.
    # Expects the model, column to check, and optional exclusion of records.
    # The exclusion is based on a column (default is 'id') and a list of values to exclude.
    def exists_as(self, model: Model, as_column, exclude_column='id', exclude_values: list=[]):
        self.rules.append(('exists_as', (model, as_column, exclude_column, exclude_values)))
        return self
    
    # Add 'regex' validation rule
    # Validates that the value matches the specified regex pattern.
    # Expects the regex pattern to be provided in the rule as 'regex:pattern'.
    def regex(self, pattern):
        self.rules.append(('regex', pattern))
        return self
    
    # Add 'in' validation rule
    # Validates that the value is included in a set of specified options.
    # Expects the options to be provided in the rule as 'in:option1,option2,...'.
    def in_options(self, options):
        self.rules.append(('in', options))
        return self
    
    # Add 'enum' validation rule
    # Validates that the value is a valid member of the specified enum class.
    # Expects the enum class to be provided in the rule as 'enum:EnumClassName'.
    def enum(self, enum_class):
        self.rules.append(('enum', enum_class))
        return self
    
    # Add 'date_range' validation rule
    # Validates that a date field falls within a specified date range.
    # Expects the date field and current time to be provided in the rule as 'date_range:dateField,currentTime'.
    def date_range(self, date_field, current_time):
        self.rules.append(('date_range', (date_field, current_time)))
        return self
    
    # Add 'date_equals' validation rule
    # Validates that a date value equals the specified comparison date.
    # Expects the comparison date to be provided in the rule as 'date_equals:comparisonDate'.
    def date_equals(self, comparison_date):
        self.rules.append(('date_equals', comparison_date))
        return self
    
    # Add 'declined' validation rule
    # Validates that the value is explicitly marked as 'declined'.
    def declined(self):
        self.rules.append(('declined', None))
        return self
    
    # Add 'declined_if' validation rule
    # Validates that the value must be 'declined' if a specified comparison field has a certain value.
    # Expects the comparison field and value in the rule as 'declined_if:comparisonField,comparisonValue'.
    def declined_if(self, comparison_field, comparison_value):
        self.rules.append(('declined_if', (comparison_field, comparison_value)))
        return self
    
    # Add 'different' validation rule
    # Validates that the value is different from the value of a specified comparison field.
    # Expects the comparison field to be provided in the rule as 'different:comparisonField'.
    def different(self, comparison_field):
        self.rules.append(('different', comparison_field))
        return self
    
    # Add 'distinct' validation rule
    # Validates that the value is a list with distinct values.
    def distinct(self):
        self.rules.append(('distinct', None))
        return self
    
    # Add 'doesnt_start_with' validation rule
    # Validates that a string value does not start with a specified prefix.
    # Expects the prefix to be provided in the rule as 'doesnt_start_with:prefix'.
    def doesnt_start_with(self, prefix):
        self.rules.append(('doesnt_start_with', prefix))
        return self
    
    # Add 'doesnt_end_with' validation rule
    # Validates that a string value does not end with a specified suffix.
    # Expects the suffix to be provided in the rule as 'doesnt_end_with:suffix'.
    def doesnt_end_with(self, suffix):
        self.rules.append(('doesnt_end_with', suffix))
        return self
    
    # Add 'extensions' validation rule
    # Validates that a file value has one of the specified extensions.
    # Expects valid extensions to be provided in the rule as 'extensions:ext1,ext2,...'.
    def extensions(self, *valid_extensions):
        self.rules.append(('extensions', valid_extensions))
        return self
    
    # Add 'filled' validation rule
    # Validates that the value is not None or an empty string.
    def filled(self):
        self.rules.append(('filled', None))
        return self
    
    # Add 'hex_color' validation rule
    # Validates that a value is a valid hex color code.
    # Expects the value to match the pattern for hex colors.
    def hex_color(self):
        self.rules.append(('hex_color', None))
        return self

    # Add 'base64' validation rule
    # Validates that the value is a valid base64 string.
    # Expects optional mime_type and max_size
    def base64(self, max_size = None):
        self.rules.append(('base64', (None, max_size)))
        return self
    
    # Add 'base64' validation rule
    # Validates that the value is a valid base64 string.
    # Expects optional mime_type and max_size
    def base64image(self, max_size = None):
        self.rules.append(('base64', ('image', max_size)))
        return self
    
    # # Add 'image' validation rule
    # # Validates that the value is a valid image file represented as bytes.
    # def base64image(self):
    #     self.rules.append(('base64image', None))
    #     return self
    
    # Add 'lowercase' validation rule
    # Validates that the value is a string and is in lowercase.
    def lowercase(self):
        self.rules.append(('lowercase', None))
        return self
    
    # Add 'uppercase' validation rule
    # Validates that the value is a string and is in uppercase.
    def uppercase(self):
        self.rules.append(('uppercase', None))
        return self
    
    # Add 'mime_type' validation rule
    # Validates that the value matches a specified MIME type.
    # Expects the desired MIME type to be provided in the rule as 'mime_type:type'.
    def mime_type(self, mime_type):
        self.rules.append(('mime_type', mime_type))
        return self
    
    # Add 'uuid' validation rule
    # Validates that the value is a valid UUID format.
    def uuid(self):
        self.rules.append(('uuid', None))
        return self
    
    # Add 'ulid' validation rule
    # Validates that the value is a valid ULID format.
    def ulid(self):
        self.rules.append(('ulid', None))
        return self
    
    # Add 'prohibited' validation rule
    # Validates that the value is prohibited (i.e., must be None).
    def prohibited(self):
        self.rules.append(('prohibited', None))
        return self
    
    # Add 'prohibited_if' validation rule
    # Validates that the value is prohibited if a specified comparison field has a certain value.
    # Expects the comparison field and value in the rule as 'prohibited_if:comparisonField,comparisonValue'.
    def prohibited_if(self, comparison_field, comparison_value):
        self.rules.append(('prohibited_if', (comparison_field, comparison_value)))
        return self
    
    # Add 'prohibited_unless' validation rule
    # Validates that the value is prohibited unless a specified comparison field has a certain value.
    # Expects the comparison field and value in the rule as 'prohibited_unless:comparisonField,comparisonValue'.
    def prohibited_unless(self, comparison_field, comparison_value):
        self.rules.append(('prohibited_unless', (comparison_field, comparison_value)))
        return self
    
    # Add 'same' validation rule
    # Validates that a value is the same as another specified field's value.
    def same(self, comparison_field):
        self.rules.append(('same', comparison_field))
        return self

    # Add 'timezone' validation rule
    # Validates that a value is a valid timezone.
    def timezone(self, timezone):
        self.rules.append(('timezone', timezone))
        return self
    
    # Add 'accepted' validation rule
    # Validates that the value must be accepted (i.e., it should be 'yes', '1', or True).
    def accepted(self):
        self.rules.append(('accepted', None))
        return self
    
    # Add 'active_url' validation rule
    # Validates that the value must be a valid URL.
    def active_url(self):
        self.rules.append(('active_url', None))
        return self
    
    # Add 'after' validation rule
    # Validates that the value must be a date after a specified comparison date.
    def after(self, comparison_date):
        self.rules.append(('after', comparison_date))
        return self
    
    # Add 'after_or_equal' validation rule
    # Validates that the value must be a date after or equal to a specified comparison date.
    def after_or_equal(self, comparison_date):
        self.rules.append(('after_or_equal', comparison_date))
        return self
    
    # Add 'alpha' validation rule
    # Validates that the value must be a string containing only alphabetic characters.
    def alpha(self):
        self.rules.append(('alpha', None))
        return self
    
    # Add 'alpha_dash' validation rule
    # Validates that the value must be alphabetic and may contain dashes or underscores.
    def alpha_dash(self):
        self.rules.append(('alpha_dash', None))
        return self
    
    # Add 'alpha_numeric' validation rule
    # Validates that the value must be alphanumeric (only letters and numbers).
    def alpha_numeric(self):
        self.rules.append(('alpha_numeric', None))
        return self
    
    # Add 'array' validation rule
    # Validates that a value is an array (list).
    def array(self, type: Type[Any] = None, min: int = 0):
        self.rules.append(('array', (type, min)))
        return self

    # Add 'ascii' validation rule
    # Validates that a value contains only ASCII characters.
    def ascii(self):
        self.rules.append(('ascii', None))
        return self

    # Add 'bail' validation rule
    # Validates that further checks should be stopped on the first validation failure.
    def bail(self):
        self.rules.append(('bail', None))
        return self

    # Add 'before' validation rule
    # Validates that the value must be a date before a specified comparison date.
    def before(self, comparison_date):
        self.rules.append(('before', comparison_date))
        return self

    # Add 'before_or_equal' validation rule
    # Validates that the value must be a date before or equal to a specified comparison date.
    def before_or_equal(self, comparison_date):
        self.rules.append(('before_or_equal', comparison_date))
        return self

    # Add 'between' validation rule
    # Validates that the value must be between two specified values.
    def between(self, min_value, max_value):
        self.rules.append(('between', f"{min_value},{max_value}"))
        return self

    # Add 'boolean' validation rule
    # Validates that the value must be a boolean (True, False, 1, or 0).
    def boolean(self):
        self.rules.append(('boolean', None))
        return self

    # Add 'contains' validation rule
    # Validates that the array contains a specified value.
    def contains(self, required_value):
        self.rules.append(('contains', required_value))
        return self

    # Add 'date' validation rule
    # Validates that the value must be a valid date in a specified format.
    def date(self, format='Y-m-d'):
        self.rules.append(('date', format))
        return self

    # Add 'date_format' validation rule
    # Validates that the date value matches a specified format string.
    def date_format(self, format_string):
        self.rules.append(('date_format', format_string))
        return self
    
    # Not In validation
    # Validates that the value must not be one of the specified invalid values.
    # Argument:
    # - invalid_values: A list of values that the value must not be in.
    def not_in(self, invalid_values):
        self.rules.append(('not_in', ','.join(invalid_values)))
        return self

    # IP Address validation
    # Validates that the value must be a valid IP address.
    def ip_address(self):
        self.rules.append(('ip_address', None))
        return self

    # JSON validation
    # Validates that the value must be a valid JSON string.
    def json(self):
        self.rules.append(('json', None))
        return self

    # Less Than validation
    # Validates that the value must be less than a specified value.
    # Argument:
    # - comparison_value: The value to compare against.
    def less_than(self, comparison_value):
        self.rules.append(('less_than', comparison_value))
        return self

    # Less Than Or Equal validation
    # Validates that the value must be less than or equal to a specified value.
    # Argument:
    # - comparison_value: The value to compare against.
    def less_than_or_equal(self, comparison_value):
        self.rules.append(('less_than_or_equal', comparison_value))
        return self

    # MAC Address validation
    # Validates that the value must be a valid MAC address.
    def mac_address(self):
        self.rules.append(('mac_address', None))
        return self
    
    # MIME Types validation
    # Validates that the value (e.g., file) must have one of the specified MIME types.
    # Argument:
    # - valid_mime_types: A list of valid MIME types for the file.
    def mime_types(self, valid_mime_types):
        self.rules.append(('mime_types', ','.join(valid_mime_types)))
        return self

    # Not Regex validation
    # Validates that the value must NOT match a specified regular expression pattern.
    # Argument:
    # - pattern: The regex pattern that the value must not match.
    def not_regex(self, pattern):
        self.rules.append(('not_regex', pattern))
        return self
    
    # Size validation
    # Validates that the length of the value matches the specified size.
    # Arguments:
    # - size_value: The expected size (length) of the value.
    def size(self, size_value):
        self.rules.append(('size', size_value))
        return self

    # Starts With validation
    # Validates that the string starts with the specified prefix.
    # Arguments:
    # - prefix: The expected prefix the string should start with.
    def starts_with(self, prefix):
        self.rules.append(('starts_with', prefix))
        return self

    # String validation
    # Validates that the value is a string.
    def string(self):
        self.rules.append(('string', None))
        return self
    
    # Custom validation
    # Validates the value using a custom function.
    # Arguments:
    # - custom_function: A callable function that will perform the custom validation logic.
    def custom(self, custom_function):
        self.rules.append(('custom', custom_function))
        return self
    
    # List validation
    # Validates that the value is a list (array).
    def list(self):
        self.rules.append(('list', None))
        return self
    
    