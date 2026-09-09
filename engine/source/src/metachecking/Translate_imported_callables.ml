module C = Imported_callables

let string value = `String value
let list f values = `A (List.map f values)

let optional key f = function
  | None -> []
  | Some value -> [ (key, f value) ]

let nonempty key f = function
  | [] -> []
  | values -> [ (key, list f values) ]

let origin value =
  [
    ("module", string value.C.module_name);
    ("symbol", list string value.C.symbol);
  ]

let builtin = function
  | C.String -> "string"
  | C.Bool -> "bool"
  | C.Int -> "int"
  | C.Float -> "float"
  | C.Number -> "number"
  | C.Null -> "null"
  | C.Undefined -> "undefined"
  | C.Unit -> "unit"
  | C.Port -> "port"
  | C.Record -> "record"

let rec type_ref = function
  | C.Builtin value -> `O [ ("builtin", string (builtin value)) ]
  | C.Union values -> `O [ ("union", list type_ref values) ]
  | C.Named (name, arguments) ->
      `O (origin name @ nonempty "arguments" type_ref arguments)
  | C.Parameter value -> `O [ ("parameter", string value) ]
  | C.Optional value -> `O [ ("optional", type_ref value) ]
  | C.Metatype value -> `O [ ("metatype", type_ref value) ]
  | C.Function (parameters, result) ->
      `O
        [
          ( "function",
            `O
              [
                ("parameters", list type_ref parameters);
                ("result", type_ref result);
              ] );
        ]
  | C.Reference (mutable_, typ) ->
      `O
        [
          ( "reference",
            `O [ ("mutable", `Bool mutable_); ("type", type_ref typ) ] );
        ]
  | C.Existential protocols ->
      `O [ ("existential", list (fun value -> `O (origin value)) protocols) ]

let kind = function
  | C.Operator -> "operator"
  | C.FunctionCall -> "function"
  | C.Method -> "method"
  | C.Property -> "property"

let receiver = function
  | C.Owned -> "owned"
  | C.Shared -> "shared"
  | C.Mutable -> "mutable"

let formal value =
  `O
    ([ ("type", type_ref value.C.typ) ]
    @ optional "label" string value.C.label
    @ (if value.C.evaluation = C.Autoclosure then
         [ ("evaluation", string "autoclosure") ]
       else [])
    @
    if value.C.cardinality = C.Variadic then
      [ ("cardinality", string "variadic") ]
    else [])

let generic value =
  `O
    ([ ("name", string value.C.parameter) ]
    @ nonempty "conforms-to"
        (fun value -> `O (origin value))
        value.C.conforms_to)

let declaration value =
  `O
    ([
       ("id", string value.C.id);
       ("origin", `O (origin value.C.origin));
       ("kind", string (kind value.C.kind));
       ("parameters", list formal value.C.parameters);
       ("result", type_ref value.C.result);
     ]
    @ optional "owner" type_ref value.C.owner
    @ optional "receiver"
        (fun value -> string (receiver value))
        value.C.receiver
    @ nonempty "generics" generic value.C.generics)

let selected_symbol value =
  `O
    ([ ("symbol", list string value.C.path) ]
    @ optional "alias" string value.C.alias
    @ optional "category" string value.C.category)

let visible_import value =
  `O
    ([
       ("module", string value.C.imported_module);
       ( "mode",
         string
           (match value.C.import_mode with
           | C.All -> "all"
           | C.Module -> "module"
           | C.Selective -> "selective") );
     ]
    @ optional "alias" string value.C.import_alias
    @ nonempty "symbols" selected_symbol value.C.selected)

let associated_type value =
  `O
    [
      ("origin", `O (origin value.C.association));
      ("type", type_ref value.C.value);
    ]

let type_fact value =
  `O
    ([ ("type", type_ref value.C.subject) ]
    @ optional "representation"
        (fun category -> string (builtin category))
        value.C.representation
    @ nonempty "conforms-to"
        (fun value -> `O (origin value))
        value.C.conformances
    @ nonempty "associated-types" associated_type value.C.associated_types)

let lookup value =
  `O
    ([
       ("kind", string (kind value.C.lookup_kind));
       ("name", string value.C.name);
       ("arguments", list formal value.C.arguments);
       ("selected", string value.C.selected_declaration);
     ]
    @ optional "receiver" type_ref value.C.lookup_receiver)

let type_binding value =
  `O
    [
      ("name", list string value.C.spelling);
      ("type", type_ref value.C.target_type);
    ]

let profile value =
  `O
    ([
       ("imports", list visible_import value.C.visible_imports);
       ("lookups", list lookup value.C.lookups);
     ]
    @ nonempty "type-facts" type_fact value.C.type_facts
    @ nonempty "type-bindings" type_binding value.C.type_bindings)
