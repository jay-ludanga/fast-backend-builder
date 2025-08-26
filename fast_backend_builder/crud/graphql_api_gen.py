# graphql_generator/generator.py

import re
# from pluralize import pluralize

from fast_backend_builder.crud.graphql_schema_gen import generate_schemas
from fast_backend_builder.utils.file import get_file_content, get_package_file, write_to_file
from fast_backend_builder.utils.str_helpers import remove_between, to_snake_case


common_template = 'fast_backend_builder.common.templates'
crud_template = 'fast_backend_builder.crud.templates'
attach_template = 'fast_backend_builder.attach.templates'
transit_template = 'fast_backend_builder.workflow.templates'

api_template_path = 'graphql_api_template.py'
type_template_path = 'gql_type_template.py'
input_template_path = 'gql_input_template.py'
model_template_path = 'model_template.py'
controller_template_path = 'controller_template.py'
schema_template_path = 'gql_schemas_template.py'
module_init_template_path = 'module_init_.py'
generated_schema_path = 'generated/graphql_crud_api.py'


def is_model(model_name: str):
    return False

def has_class(filename, classname):
    content = get_file_content(filename)
    if content:
        # Regex pattern to match 'class', followed by any whitespace, then the classname
        pattern = r"\bclass\s+" + re.escape(classname) + r"\b"
        return re.search(pattern, content) is not None
    return None

def generate_schema(module, module_package:str,  models_str: str, with_controller: bool, create_multiple: bool, with_attachment: bool, with_transition: bool):
    type_template = get_package_file(crud_template, type_template_path)
    if not type_template:
        return
    
    attachment_type_template = get_package_file(attach_template, type_template_path)
    if not attachment_type_template:
        return

    attachment_input_template = get_package_file(attach_template, input_template_path)
    if not attachment_input_template:
        return

    transit_type_template = get_package_file(transit_template, type_template_path)
    if not transit_type_template:
        return

    input_template = get_package_file(crud_template, input_template_path)
    if not input_template:
        return

    if with_controller:
        controller_template = get_package_file(crud_template, controller_template_path)
        if not controller_template:
            return

    module_path = f"modules/{module}"
    schemas_path = f"{module_path}/schemas"

    # module_model = get_file_content(f"{module_path}/models.py")
    # if module_model == False:
    #     module_model = ""

    module_request = get_file_content(f"{schemas_path}/request.py")
    if module_request == False:
        module_request = ""

    module_response = get_file_content(f"{schemas_path}/response.py")
    if module_response == False:
        module_response = ""

    api_template = get_package_file(crud_template, api_template_path)
    if not api_template:
        return

    schema_template = get_file_content(generated_schema_path)
    if not schema_template:
        schema_template = get_package_file(crud_template, schema_template_path)
        if not schema_template:
            return
        has_schemas = False
    else:
        has_schemas = True

    module_api = get_file_content(f"{module_path}/api.py")
    if module_api == False:
        module_init = get_package_file(common_template, f"{module_init_template_path}")
        write_to_file(f"modules/__init__.py", module_init)
        write_to_file(f"{module_path}/api.py", "'''Module API File'''")
        

    models = models_str.replace(' ', '').split(',')
        
    query_schemas = None
    mutation_schemas = None
    api_imports = None

    for model_name in models:
        # Create CRUD Quaries and Mutations
        real_api_template = api_template.replace('_MODEL_', f"{model_name}") \
            .replace('_model_', f"{to_snake_case(model_name)}") \
            .replace('_flatmodel_', f"{to_snake_case(model_name).replace('_', '')}") \
            .replace('_models_', f"{to_snake_case(model_name)}s") \
            .replace('ResponseType', f"{model_name}Response") \
            .replace('UpdateType', f"{model_name}Update") \
            .replace('CreateType', f"{model_name}Create") \
            .replace('Model', f"{model_name}")

        real_api_template = f"from {module_package} import {model_name}\n" + \
                            f"from modules.{module}.schemas.request import *\n" + \
                            f"from modules.{module}.schemas.response import *\n" + \
                            f"\n{real_api_template.split("'''Imports'''")[1]}"

        # Add Create Multiple endpoint
        if create_multiple:
            real_api_template = real_api_template.replace("\n'''CREATE_MULTIPLE'''", '').replace("\n'''CREATE_MULTIPLE_END'''", '')
        else:
            # Remove Attachments Queries
            real_api_template = remove_between(real_api_template, 
                                    "'''CREATE_MULTIPLE'''", 
                                    "'''CREATE_MULTIPLE_END'''"
                                )
            
        # Create Attachment Quaries and Mutations
        if with_attachment:
            real_api_template = real_api_template.replace(f"from fast_backend_builder.attach.response import {model_name}AttachmentResponse", '')\
                                                .replace(f"from fast_backend_builder.attach.request import {model_name}Attachment", '')
        else:
            # Remove Attachments Queries
            real_api_template = remove_between(real_api_template, 
                                    "'''ATTACHMENT_QUERIES'''", 
                                    "'''ATTACHMENT_QUERIES_END'''"
                                )
            # Remove Attachments Mutations
            real_api_template = remove_between(real_api_template, 
                                    "'''ATTACHMENT_MUTATIONS'''", 
                                    "'''ATTACHMENT_MUTATIONS_END'''"
                                )
            
            # Also remove imports
            real_api_template = real_api_template.replace(f"from fast_backend_builder.attach.response import {model_name}AttachmentResponse", '')\
                                                .replace(f"from fast_backend_builder.attach.request import {model_name}Attachment", '')
                                                
        # Create Attachment Quaries and Mutations
        if with_transition:
            real_api_template = real_api_template.replace(f"from fast_backend_builder.workflow.response import {model_name}EvaluationStatusResponse", '')
        else:
            # Remove Attachments Queries
            real_api_template = remove_between(real_api_template, 
                                    "'''EVALUATION_QUERIES'''", 
                                    "'''EVALUATION_QUERIES_END'''"
                                )
            # Remove Attachments Mutations
            real_api_template = remove_between(real_api_template, 
                                    "'''EVALUATION_MUTATIONS'''", 
                                    "'''EVALUATION_MUTATIONS_END'''"
                                )
            
            # Also remove imports
            real_api_template = real_api_template.replace(f"from fast_backend_builder.workflow.response import {model_name}EvaluationStatusResponse", '')\
                                                .replace('from fast_backend_builder.workflow.request import EvaluationStatus', '')

        api_schema_file_name = f"{to_snake_case(model_name)}_crud_api.py"
        
        schema_fields = generate_schemas(module_package, model_name)
        if schema_fields:
            schema_fields = schema_fields.get(model_name)
        else:
            print(f"Model with name: {model_name} does not exist in models list")
            break
        
        # Create controller template classes
        if with_controller:
            controller_path = f"{module_path}/controllers/{to_snake_case(model_name)}.py"
            if not has_class(controller_path, f"{model_name}Controller"):
                real_controller_template = controller_template.replace('_MODEL_', f"{model_name}")\
                                .replace(f"'''IMPORTS'''", f"from modules.{module}.schemas.request import *").replace('_MODELPACKAGE_', module_package)
                output_file = f"{module_path}/controllers/{to_snake_case(model_name)}.py"
                print(f"Writing {model_name} controller in: {output_file}")
                write_to_file(output_file, real_controller_template)
                
            real_api_template = real_api_template.replace('fast_backend_builder.crud.gql_controller', f"modules.{module}.controllers.{to_snake_case(model_name)}")\
                            .replace('GQLBaseCRUD', f"{model_name}Controller")
            
        create_fields = []
        for field, type in schema_fields.items():
            create_fields.append(f"{field}: {type}")
        
        if not has_class(f"{schemas_path}/request.py", f"{model_name}Create"):
            real_input_template = input_template.replace('_MODEL_', f"{model_name}")\
                                                .replace("'''CREATE'''", "\n    ".join(create_fields))
            if module_request == "":
                module_request += f"{real_input_template}"
            else:
                module_request += f"\n{real_input_template.split("'''List of Inputs'''")[1]}"
                
        # Create attachment request schema classes
        if with_attachment:
            if not has_class(f"{schemas_path}/request.py", f"{model_name}Attachment"):
                real_attachment_input_template = attachment_input_template.replace('_MODEL_', f"{model_name}")
                module_request += f"\n{real_attachment_input_template.split("'''ATTACHMENT_UPLOAD'''")[1]}"
                
                if not module_request.__contains__("from fast_backend_builder.attach.request import AttachmentUpload"):
                    module_request = module_request.split("'''List of Inputs'''")[0] \
                        + "from fast_backend_builder.attach.request import AttachmentUpload"\
                        + "\n'''List of Inputs'''"\
                        + f"\n{module_request.split("'''List of Inputs'''")[1]}"
            
        # Create response schema classes
        if not has_class(f"{schemas_path}/response.py", f"{model_name}Response"):
            real_type_template = type_template.replace('_MODEL_', f"{model_name}")\
                                                .replace("'''FIELDS'''", "\n    ".join(create_fields))\
                                                .replace(': str', ': Optional[str] = None')\
                                                .replace(': int', ': Optional[int] = None')\
                                                .replace(': float', ': Optional[float] = None')\
                                                .replace(': bool', ': Optional[bool] = None')
            
            if module_response == "":
                module_response += f"{real_type_template}"
            else:
                module_response += f"\n{real_type_template.split("'''List of Types'''")[1]}"
                
        # Create attachment response schema classes
        if with_attachment:
            if not has_class(f"{schemas_path}/response.py", f"{model_name}AttachmentResponse"):
                real_attachment_type_template = attachment_type_template.replace('_MODEL_', f"{model_name}")
                module_response += f"\n{real_attachment_type_template.split("'''ATTACHMENT_RESPONSE'''")[1]}"
                
                if not module_response.__contains__("from fast_backend_builder.attach.response import AttachmentResponse"):
                    module_response = module_response.split("'''List of Types'''")[0] \
                        + "from fast_backend_builder.attach.response import AttachmentResponse"\
                        + "\n'''List of Types'''"\
                        + f"\n{module_response.split("'''List of Types'''")[1]}"
                                
        # Create attachment response schema classes
        if with_transition:
            if not has_class(f"{schemas_path}/response.py", f"{model_name}EvaluationStatusResponse"):
                transit_type_template = transit_type_template.replace('_MODEL_', f"{model_name}")
                module_response += f"\n{transit_type_template.split("'''EVALUATION_RESPONSE'''")[1]}"
                
                if not module_response.__contains__("from fast_backend_builder.workflow.response import EvaluationStatusResponse"):
                    module_response = module_response.split("'''List of Types'''")[0] \
                        + "from fast_backend_builder.workflow.response import EvaluationStatusResponse"\
                        + "\n'''List of Types'''"\
                        + f"\n{module_response.split("'''List of Types'''")[1]}"
        
        # Create impotrs of  individual schemas
        if  isinstance(schema_template, str) and not schema_template.__contains__(api_schema_file_name.split('.')[0]):
            
            if api_imports:
                api_imports += f"\nfrom .{api_schema_file_name.split('.')[0]} import *"
            else:
                api_imports = f"from .{api_schema_file_name.split('.')[0]} import *"

            # Extend from individual schemas
            if query_schemas:
                query_schemas += (f",{model_name}Query")
                mutation_schemas += (f",{model_name}Mutation")
            else:
                query_schemas = (f"{model_name}Query")
                mutation_schemas = (f"{model_name}Mutation")

        # Write model schema file
        output_file = f"generated/{api_schema_file_name}"
        print(f"Writing {model_name} graphql apis in: {output_file}")
        write_to_file(output_file, real_api_template)

    # Import Queries and Mutations
    if api_imports:
        schema_template = schema_template.replace("'''IMPORTS'''", f"'''IMPORTS'''\n{api_imports}")

    # Extend Queries and Mutations
    if query_schemas:
        if has_schemas:
            schema_template = schema_template.replace('CRUDQuery(', f"CRUDQuery({query_schemas},") \
                .replace('CRUDMutation(', f"CRUDMutation({mutation_schemas},")
        else:
            schema_template = schema_template.replace('CRUDQuery(', f"CRUDQuery({query_schemas}") \
                .replace('CRUDMutation(', f"CRUDMutation({mutation_schemas}")

    # write_to_file(f"{module_path}/models.py", module_model)
    print(f"Writing request schemas in: {schemas_path}/request.py")
    write_to_file(f"{schemas_path}/request.py", module_request)
    
    print(f"Writing response schemas in: {schemas_path}/request.py")
    write_to_file(f"{schemas_path}/response.py", module_response)
    
    print(f"Writing combined CRUD Schemas in: generated/graphql_crud_api.py")
    write_to_file("generated/graphql_crud_api.py", schema_template)

    print(f"Code Generation completed successfully")


if __name__ == "__main__":
    generate_schema('app', None, True)
