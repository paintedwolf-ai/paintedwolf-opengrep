let ( let/ ) = Result.bind

open Parse_rule_helpers
module C = Imported_callables
module H = Parse_rule_helpers

let fail env key message = error_at_key env.id key message

let consumed env key dict =
  if Hashtbl.length dict.H.h = 0 then Ok ()
  else fail env key "Unknown or duplicate callable model properties"

let name env key value =
  let/ value = parse_string env key value in
  if String.equal value "" || String.length value > 256 then
    fail env key "Callable model names require 1 to 256 bytes"
  else Ok value

let bounded_list maximum parser env key value =
  let/ values = parse_list env key (fun env -> parser env key) value in
  if List.length values > maximum then
    fail env key "Callable model list exceeds its bound"
  else Ok values

let distinct values =
  List.length values = List.length (List.sort_uniq Stdlib.compare values)

let nonempty_list maximum parser env key value =
  let/ values = bounded_list maximum parser env key value in
  if values = [] || not (distinct values) then
    fail env key "Expected a nonempty list of distinct callable model values"
  else Ok values

let symbol_path env key value =
  let/ values = bounded_list 16 name env key value in
  if values = [] then fail env key "Expected a nonempty symbol path"
  else Ok values

let origin env key value =
  let/ dict = parse_dict env key value in
  let/ module_name = take_key dict env name "module" in
  let/ symbol = take_key dict env symbol_path "symbol" in
  let/ () = consumed env key dict in
  Ok { C.module_name; symbol }

let choice choices env key value =
  let/ spelling = name env key value in
  match List.assoc_opt spelling choices with
  | Some value -> Ok value
  | None -> fail env key "Unknown callable model enum value"

let kind =
  choice
    [
      ("operator", C.Operator);
      ("function", C.FunctionCall);
      ("method", C.Method);
      ("property", C.Property);
    ]

let evaluation = choice [ ("eager", C.Eager); ("autoclosure", C.Autoclosure) ]
let cardinality = choice [ ("fixed", C.Fixed); ("variadic", C.Variadic) ]

let receiver =
  choice [ ("owned", C.Owned); ("shared", C.Shared); ("mutable", C.Mutable) ]

let builtin =
  choice
    [
      ("string", C.String);
      ("bool", C.Bool);
      ("int", C.Int);
      ("float", C.Float);
      ("number", C.Number);
      ("null", C.Null);
      ("undefined", C.Undefined);
      ("unit", C.Unit);
      ("port", C.Port);
      ("record", C.Record);
    ]

let import_mode =
  choice [ ("all", C.All); ("module", C.Module); ("selective", C.Selective) ]

let rec type_ref budget depth env key value =
  decr budget;
  if depth > 16 || !budget < 0 then
    fail env key "Callable type model exceeds depth or node budget"
  else
    let/ dict = parse_dict env key value in
    let child = type_ref budget (depth + 1) in
    let/ primitive = take_opt dict env builtin "builtin" in
    let/ union = take_opt dict env (nonempty_list 32 child) "union" in
    let/ module_name = take_opt dict env name "module" in
    let/ value =
      match (primitive, union, module_name) with
      | Some value, None, None -> Ok (C.Builtin value)
      | None, Some values, None when List.length values > 1 ->
          let values =
            List.concat_map
              (function
                | C.Union values -> values
                | value -> [ value ])
              values
          in
          let normalized = List.sort_uniq C.compare_type_ref values in
          if List.length normalized <> List.length values then
            fail env key "Duplicate alternative in callable union"
          else Ok (C.Union normalized)
      | None, None, module_name -> (
          match module_name with
          | Some module_name ->
              let/ symbol = take_key dict env symbol_path "symbol" in
              let/ arguments =
                take_opt dict env (bounded_list 64 child) "arguments"
              in
              Ok
                (C.Named
                   ({ module_name; symbol }, Option.value ~default:[] arguments))
          | None -> (
              let/ parameter = take_opt dict env name "parameter" in
              match parameter with
              | Some parameter -> Ok (C.Parameter parameter)
              | None -> (
                  let/ optional = take_opt dict env child "optional" in
                  match optional with
                  | Some typ -> Ok (C.Optional typ)
                  | None -> (
                      let/ metatype = take_opt dict env child "metatype" in
                      match metatype with
                      | Some typ -> Ok (C.Metatype typ)
                      | None -> (
                          let/ reference =
                            take_opt dict env
                              (fun env key value ->
                                let/ dict = parse_dict env key value in
                                let/ mutable_ =
                                  take_key dict env parse_bool "mutable"
                                in
                                let/ typ = take_key dict env child "type" in
                                let/ () = consumed env key dict in
                                Ok (C.Reference (mutable_, typ)))
                              "reference"
                          in
                          match reference with
                          | Some typ -> Ok typ
                          | None -> (
                              let/ existential =
                                take_opt dict env (nonempty_list 32 origin)
                                  "existential"
                              in
                              match existential with
                              | Some protocols ->
                                  Ok
                                    (C.Existential
                                       (List.sort C.compare_origin protocols))
                              | None ->
                                  let/ fn =
                                    take_key dict env
                                      (fun env key value ->
                                        let/ dict = parse_dict env key value in
                                        let/ parameters =
                                          take_key dict env
                                            (bounded_list 64 child) "parameters"
                                        in
                                        let/ result =
                                          take_key dict env child "result"
                                        in
                                        let/ () = consumed env key dict in
                                        Ok (C.Function (parameters, result)))
                                      "function"
                                  in
                                  Ok fn))))))
      | _ -> fail env key "A callable type requires one type constructor"
    in
    let/ () = consumed env key dict in
    Ok value

let rec variables = function
  | C.Builtin _ -> []
  | C.Union values -> List.concat_map variables values
  | C.Parameter value -> [ value ]
  | C.Named (_, arguments) -> List.concat_map variables arguments
  | C.Optional typ
  | C.Metatype typ
  | C.Reference (_, typ) ->
      variables typ
  | C.Function (parameters, result) ->
      List.concat_map variables (result :: parameters)
  | C.Existential _ -> []

let closed_type env key value =
  let/ typ = type_ref (ref 16384) 0 env key value in
  if variables typ <> [] then
    fail env key "Closed callable type cannot reference generic parameters"
  else Ok typ

let formal budget env key value =
  let/ dict = parse_dict env key value in
  let/ label = take_opt dict env name "label" in
  let/ typ = take_key dict env (type_ref budget 0) "type" in
  let/ evaluation = take_opt dict env evaluation "evaluation" in
  let/ cardinality = take_opt dict env cardinality "cardinality" in
  let/ () = consumed env key dict in
  let evaluation = Option.value ~default:C.Eager evaluation in
  let cardinality = Option.value ~default:C.Fixed cardinality in
  match (evaluation, typ, cardinality) with
  | C.Autoclosure, C.Function ([], _), C.Fixed
  | C.Eager, _, _ ->
      Ok { C.label; typ; evaluation; cardinality }
  | _ ->
      fail env key "Autoclosure requires a fixed zero-parameter function type"

let valid_formals parameters =
  let rec loop = function
    | [] -> true
    | [ { C.cardinality = C.Variadic; _ } ] -> true
    | { C.cardinality = C.Fixed; _ } :: rest -> loop rest
    | _ -> false
  in
  loop parameters

let generic env key value =
  let/ dict = parse_dict env key value in
  let/ parameter = take_key dict env name "name" in
  let/ conforms_to =
    take_opt dict env (nonempty_list 32 origin) "conforms-to"
  in
  let/ () = consumed env key dict in
  Ok { C.parameter; conforms_to = Option.value ~default:[] conforms_to }

let declaration budget env key value =
  let/ dict = parse_dict env key value in
  let/ id = take_key dict env name "id" in
  let/ origin = take_key dict env origin "origin" in
  let/ kind = take_key dict env kind "kind" in
  let/ owner = take_opt dict env (type_ref budget 0) "owner" in
  let/ receiver = take_opt dict env receiver "receiver" in
  let/ generics = take_opt dict env (bounded_list 32 generic) "generics" in
  let generics = Option.value ~default:[] generics in
  let/ parameters =
    take_key dict env (bounded_list 64 (formal budget)) "parameters"
  in
  let/ result = take_key dict env (type_ref budget 0) "result" in
  let/ () = consumed env key dict in
  let generic_names = List.map (fun value -> value.C.parameter) generics in
  let referenced =
    List.concat_map variables
      ((result :: Option.to_list owner)
      @ List.map (fun value -> value.C.typ) parameters)
  in
  if
    (not (distinct generic_names))
    || List.exists (fun value -> not (List.mem value generic_names)) referenced
  then fail env key "Duplicate or undeclared callable type parameter"
  else if not (valid_formals parameters) then
    fail env key "Only the final callable parameter may be variadic"
  else if
    (kind = C.Method || kind = C.Property)
    && (Option.is_none owner || Option.is_none receiver)
  then fail env key "Member callable requires owner and receiver mode"
  else if
    (kind = C.FunctionCall || kind = C.Operator) && Option.is_some receiver
  then fail env key "Function or operator cannot declare a receiver mode"
  else if kind = C.Property && parameters <> [] then
    fail env key "Property callable cannot declare parameters"
  else Ok { C.id; origin; kind; owner; receiver; generics; parameters; result }

let selected_symbol env key value =
  let/ dict = parse_dict env key value in
  let/ path = take_key dict env symbol_path "symbol" in
  let/ alias = take_opt dict env name "alias" in
  let/ category = take_opt dict env name "category" in
  let/ () = consumed env key dict in
  Ok { C.path; alias; category }

let visible_import env key value =
  let/ dict = parse_dict env key value in
  let/ imported_module = take_key dict env name "module" in
  let/ import_mode = take_key dict env import_mode "mode" in
  let/ import_alias = take_opt dict env name "alias" in
  let/ selected =
    take_opt dict env (nonempty_list 64 selected_symbol) "symbols"
  in
  let selected = Option.value ~default:[] selected in
  let/ () = consumed env key dict in
  if
    import_mode = C.Selective <> (selected <> [])
    || (import_mode = C.Selective && Option.is_some import_alias)
  then
    fail env key
      "Selective import requires symbols and cannot have a module alias"
  else
    Ok
      {
        C.imported_module;
        import_mode;
        import_alias;
        selected = List.sort C.compare_selected_symbol selected;
      }

let associated_type budget env key value =
  let/ dict = parse_dict env key value in
  let/ association = take_key dict env origin "origin" in
  let/ value = take_key dict env (type_ref budget 0) "type" in
  let/ () = consumed env key dict in
  Ok { C.association; value }

let rec permits_representation representation = function
  | C.Named _ -> true
  | C.Builtin actual ->
      actual = representation
      || (representation = C.Number && (actual = C.Int || actual = C.Float))
  | C.Union alternatives ->
      List.for_all (permits_representation representation) alternatives
  | _ -> false

let type_fact budget env key value =
  let/ dict = parse_dict env key value in
  let/ subject = take_key dict env (type_ref budget 0) "type" in
  let/ representation = take_opt dict env builtin "representation" in
  let/ conformances =
    take_opt dict env (nonempty_list 32 origin) "conforms-to"
  in
  let/ associated_types =
    take_opt dict env
      (bounded_list 32 (associated_type budget))
      "associated-types"
  in
  let conformances = Option.value ~default:[] conformances in
  let associated_types = Option.value ~default:[] associated_types in
  let/ () = consumed env key dict in
  if
    List.exists
      (fun typ -> variables typ <> [])
      (subject :: List.map (fun value -> value.C.value) associated_types)
  then fail env key "Profile type facts cannot reference generic parameters"
  else if
    not
      (distinct (List.map (fun value -> value.C.association) associated_types))
  then fail env key "Duplicate associated type fact"
  else if
    Option.fold ~none:false
      ~some:(fun category -> not (permits_representation category subject))
      representation
  then fail env key "Runtime representation contradicts the declared type"
  else Ok { C.subject; conformances; associated_types; representation }

let lookup budget env key value =
  let/ dict = parse_dict env key value in
  let/ lookup_kind = take_key dict env kind "kind" in
  let/ lookup_name = take_key dict env name "name" in
  let/ lookup_receiver = take_opt dict env (type_ref budget 0) "receiver" in
  let/ arguments =
    take_key dict env (bounded_list 64 (formal budget)) "arguments"
  in
  let/ selected_declaration = take_key dict env name "selected" in
  let/ () = consumed env key dict in
  if
    (not (valid_formals arguments))
    || List.exists (fun value -> value.C.evaluation <> C.Eager) arguments
  then
    fail env key
      "Lookup arguments require eager value types and at most a final variadic \
       argument"
  else if
    (lookup_kind = C.Method || lookup_kind = C.Property)
    <> Option.is_some lookup_receiver
  then
    fail env key
      "Member lookup requires a receiver; function and operator lookup cannot \
       have one"
  else if lookup_kind = C.Property && arguments <> [] then
    fail env key "Property lookup cannot declare arguments"
  else
    Ok
      {
        C.lookup_kind;
        name = lookup_name;
        lookup_receiver;
        arguments;
        selected_declaration;
      }

let type_binding budget env key value =
  let/ dict = parse_dict env key value in
  let/ spelling = take_key dict env symbol_path "name" in
  let/ target_type = take_key dict env (type_ref budget 0) "type" in
  let/ () = consumed env key dict in
  if variables target_type <> [] then
    fail env key "Type name binding cannot reference generic parameters"
  else Ok { C.spelling; target_type }

let profile budget env key value =
  let/ dict = parse_dict env key value in
  let/ visible_imports =
    take_key dict env (bounded_list 64 visible_import) "imports"
  in
  let/ type_bindings =
    take_opt dict env (bounded_list 128 (type_binding budget)) "type-bindings"
  in
  let type_bindings = Option.value ~default:[] type_bindings in
  let/ type_facts =
    take_opt dict env (bounded_list 128 (type_fact budget)) "type-facts"
  in
  let type_facts = Option.value ~default:[] type_facts in
  let/ lookups =
    take_key dict env (bounded_list 256 (lookup budget)) "lookups"
  in
  let/ () = consumed env key dict in
  let lookup_keys =
    List.map
      (fun value ->
        ( value.C.lookup_kind,
          value.C.name,
          value.C.lookup_receiver,
          value.C.arguments ))
      lookups
  in
  if
    (not (distinct (List.map (fun value -> value.C.spelling) type_bindings)))
    || (not (distinct visible_imports))
    || (not (distinct (List.map (fun value -> value.C.subject) type_facts)))
    || not (distinct lookup_keys)
  then
    fail env key
      "Duplicate import, type fact, or typed lookup in callable profile"
  else Ok { C.visible_imports; type_facts; type_bindings; lookups }

let validate env key declarations profiles =
  let ids = List.map (fun value -> value.C.id) declarations in
  let environments =
    List.map
      (fun value -> List.sort Stdlib.compare value.C.visible_imports)
      profiles
  in
  let invalid_lookup lookup =
    match
      List.find_opt
        (fun value -> String.equal value.C.id lookup.C.selected_declaration)
        declarations
    with
    | None -> true
    | Some declaration ->
        let referenced =
          List.concat_map variables
            (Option.to_list lookup.C.lookup_receiver
            @ List.map (fun value -> value.C.typ) lookup.C.arguments)
        in
        declaration.C.kind <> lookup.C.lookup_kind
        || List.exists
             (fun value ->
               not
                 (List.exists
                    (fun generic -> String.equal generic.C.parameter value)
                    declaration.C.generics))
             referenced
  in
  if not (distinct ids) then fail env key "Duplicate callable declaration id"
  else if not (distinct environments) then
    fail env key "Duplicate callable import environment"
  else if
    List.exists
      (fun value -> List.exists invalid_lookup value.C.lookups)
      profiles
  then
    fail env key
      "Callable lookup has an unknown declaration, mismatched kind, or \
       undeclared parameter"
  else Ok ()
