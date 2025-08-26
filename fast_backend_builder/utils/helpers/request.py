from fast_backend_builder.utils.str_helpers import to_snake_case


def resolve_request_fields(info):
    try:
        selected = info.selected_fields[0].selections
        for field in selected:
            if field.name == 'data':
                for fn in field.selections:
                    if fn.name == 'items':
                        return [to_snake_case(f.name) for f in fn.selections]
                return [to_snake_case(f.name )for f in field.selections]
        
    except Exception as e:
        print(str(e))
    
    return []