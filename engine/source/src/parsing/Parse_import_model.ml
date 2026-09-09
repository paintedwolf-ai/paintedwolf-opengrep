open Common
open Parse_rule_helpers
module H = Parse_rule_helpers
module R = Rule

let nonempty env key value =
  let/ name = parse_string env key value in
  if String.equal name "" then
    error_at_key env.id key "Expected a nonempty import name"
  else Ok name

let fields_consumed env key dict =
  if Hashtbl.length dict.H.h > 0 then
    error_at_key env.id key "Unknown or duplicate import model properties"
  else Ok ()

let names env key value = parse_list env key (fun env -> nonempty env key) value

let origin env key value =
  let/ dict = parse_dict env key value in
  let/ module_name = take_key dict env nonempty "module" in
  let/ symbol_path = take_key dict env names "symbol" in
  let/ () = fields_consumed env key dict in
  if List.length symbol_path < 1 || List.length symbol_path > 16 then
    error_at_key env.id key "Export origin requires 1 to 16 symbol components"
  else Ok (module_name, symbol_path)

let export env key value =
  let/ dict = parse_dict env key value in
  let/ export_module = take_key dict env nonempty "module" in
  let/ export_name = take_key dict env nonempty "symbol" in
  let/ absent = take_opt dict env parse_bool "absent" in
  let/ export_origin = take_opt dict env origin "origin" in
  let/ () = fields_consumed env key dict in
  match (absent, export_origin) with
  | Some true, None
  | None, Some _ ->
      Ok { R.export_module; export_name; export_origin }
  | _ ->
      error_at_key env.id key
        "An export fact requires absent: true or an origin"

let complete_exports env key value =
  let/ dict = parse_dict env key value in
  let/ complete_module = take_key dict env nonempty "module" in
  let/ complete_symbols = take_key dict env names "symbols" in
  let/ () = fields_consumed env key dict in
  let unique = List.sort_uniq String.compare complete_symbols in
  if List.length complete_symbols > 512 then
    error_at_key env.id key "Complete module exports exceed 512 symbols"
  else if not (Int.equal (List.length unique) (List.length complete_symbols)) then
    error_at_key env.id key "Duplicate symbol in complete module exports"
  else Ok { R.complete_module; complete_symbols }

let parse env key value =
  let/ dict = parse_dict env key value in
  let/ implicit = take_opt dict env names "implicit" in
  let/ exports =
    take_opt dict env
      (fun env key value ->
        parse_list env key (fun env -> export env key) value)
      "exports"
  in
  let/ complete =
    take_opt dict env
      (fun env key value -> parse_list env key (fun env -> complete_exports env key) value)
      "complete-exports"
  in
  let budget = ref 16384 in
  let/ callables = take_opt dict env
    (Parse_imported_callables.bounded_list 128 (Parse_imported_callables.declaration budget)) "callables" in
  let/ callable_profiles = take_opt dict env
    (Parse_imported_callables.bounded_list 128 (Parse_imported_callables.profile budget)) "callable-profiles" in
  let callables = Option.value ~default:[] callables in
  let callable_profiles = Option.value ~default:[] callable_profiles in
  let/ () = Parse_imported_callables.validate env key callables callable_profiles in
  let/ () = fields_consumed env key dict in
  let complete_exports = Option.value ~default:[] complete in
  let implicit_modules = Option.value ~default:[] implicit in
  let export_facts = Option.value ~default:[] exports in
  let seen = Hashtbl.create 16 in
  let duplicate =
    List.exists
      (fun fact ->
        let key = (fact.R.export_module, fact.R.export_name) in
        let exists = Hashtbl.mem seen key in
        Hashtbl.replace seen key ();
        exists)
      export_facts
  in
  let complete_modules = List.map (fun value -> value.R.complete_module) complete_exports in
  let complete_unique = List.sort_uniq String.compare complete_modules in
  let complete_symbol_count = List.fold_left
      (fun count value -> count + List.length value.R.complete_symbols) 0 complete_exports in
  let conflicting_fact = List.exists (fun fact ->
      match List.find_opt (fun value -> String.equal value.R.complete_module fact.R.export_module) complete_exports with
      | None -> false
      | Some value ->
          Option.is_none fact.R.export_origin
          || not (List.mem fact.R.export_name value.R.complete_symbols)) export_facts in
  let implicit_unique = List.sort_uniq String.compare implicit_modules in
  if
    not (Int.equal (List.length implicit_unique) (List.length implicit_modules))
  then error_at_key env.id key "Duplicate implicit module"
  else if duplicate then
    error_at_key env.id key "Duplicate export model for a module and symbol"
  else if not (Int.equal (List.length complete_unique) (List.length complete_modules)) then
    error_at_key env.id key "Duplicate complete module export declaration"
  else if conflicting_fact then
    error_at_key env.id key "Partial export facts for a complete module must give origins for declared symbols"
  else if List.length complete_exports > 64 || complete_symbol_count > 4096 then
    error_at_key env.id key "Complete export model exceeds 64 modules or 4096 total symbols"
  else if List.length implicit_modules > 64 || List.length export_facts > 512
  then
    error_at_key env.id key
      "Import model exceeds 64 implicit modules or 512 export facts"
  else if List.is_empty implicit_modules && List.is_empty export_facts && List.is_empty complete_exports && List.is_empty callables && List.is_empty callable_profiles then
    error_at_key env.id key
      "Import model must declare implicit modules, export facts, or complete exports"
  else Ok { R.implicit_modules; export_facts; complete_exports; callables; callable_profiles }
