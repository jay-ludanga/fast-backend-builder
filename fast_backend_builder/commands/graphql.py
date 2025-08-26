import argparse
from fast_backend_builder.crud.graphql_api_gen import generate_schema as gen_crud_schema

def add_arguments(parser: argparse.ArgumentParser):    
    subparsers = parser.add_subparsers(dest='command', description='Graphql API generator')
    
    crud_purser = subparsers.add_parser('gen:crud-api', help='Generate CRUD GraphQL Apis')

    crud_purser.add_argument(
        "--models",
        type=str, 
        required=True,
        help="Specify comma separated models for which to generate graphql schema"
    )
    
    crud_purser.add_argument(
        "module", 
        type=str,
        help="Module folder in which to generate code"
    )


    crud_purser.add_argument(
        "--module-package",
        type=str,
        required=True,
        help="Module Package in which to Models of the module contains"
    )

    crud_purser.add_argument(
        "--with-controller", 
        type=bool, 
        default=True,
        help="Generate with Controller"
    )
    
    crud_purser.add_argument(
        "--with-attachment", 
        action="store_true",
        help="Add attachment queries and mutations"
    )
    
    crud_purser.add_argument(
        "--with-transition", 
        action="store_true",
        help="Add transition queries and mutations"
    )
    
    crud_purser.add_argument(
        "--create-multiple", 
        action="store_true",
        help="Add multiple create query"
    )
    return parser

def main():
    parser = argparse.ArgumentParser(description="Generate GraphQL schema.")
    parser = add_arguments(parser)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        exit(1)
    if args.command == 'gen:crud-api':
        models = args.models if args.models else None
        with_controller = args.with_controller if args.with_controller else False
        with_attachment = args.with_attachment if args.with_attachment else False
        create_multiple = args.create_multiple if args.create_multiple else False
        with_transition = args.with_transition if args.with_transition else False

        gen_crud_schema(args.module, args.module_package, models, with_controller, create_multiple, with_attachment, with_transition)


if __name__ == "__main__":
    main()