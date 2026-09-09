module G = AST_generic
module Names = IL.NameMap

type value = Unknown | Literal of G.literal | Sequence of IL.composite_kind * value list
type t = value Names.t
let empty = Names.empty

let rec expression = function
  | Unknown -> IL.{ e = FixmeExp (ToDo, G.Tk G.sc, None); eorig = NoOrig }
  | Literal value -> IL.{ e = Literal value; eorig = NoOrig }
  | Sequence (kind, values) ->
      IL.{ e = Composite (kind, (G.sc, List.map expression values, G.sc)); eorig = NoOrig }

let equal_value left right = IL_helpers.equal_exp (expression left) (expression right)
let equal = Names.equal equal_value
let join = Names.merge (fun _ left right -> match left, right with
  | Some left, Some right when equal_value left right -> Some left
  | _ -> None)
let remove = Names.remove
let filter = Names.filter

exception Value_limit

let evaluate lang values depth expr =
  let remaining = ref 256 in
  let spend () = decr remaining; if !remaining < 0 then raise Value_limit in
  let rec bounded_map f remaining = function
    | [] -> []
    | _ when remaining = 0 -> raise Value_limit
    | item :: rest -> let value = f item in value :: bounded_map f (remaining - 1) rest in
  let rec charge = function
    | Unknown | Literal _ -> spend ()
    | Sequence (_, items) -> spend (); List.iter charge items in
  let rec evaluate depth expr =
    spend ();
    if depth > 32 then raise Value_limit;
    let eval = evaluate (depth + 1) in
    let primitive expr =
      match Eval_il_partial.eval (Eval_il_partial.mk_env lang Dataflow_var_env.VarMap.empty) expr with
      | G.Lit value -> Literal value
      | _ -> Unknown in
    match expr.IL.e with
    | Literal value -> Literal value
    | Fetch { base = Var name; rev_offset } ->
        let rec project value = function
          | [] -> value
          | offset :: rest ->
              let selected = match offset.IL.o, value with
                | Index index, Sequence (_, items) ->
                    (match eval index with
                    | Literal (G.Int index) ->
                        (match Parsed_int.to_int_opt index with
                        | Some index when index >= 0 -> Option.value ~default:Unknown (List.nth_opt items index)
                        | _ -> Unknown)
                    | _ -> Unknown)
                | Slice index, Sequence (kind, items) when index >= 0 ->
                    Sequence (kind, List.filteri (fun i _ -> i >= index) items)
                | _ -> Unknown in
              project selected rest in
        let value = project (Option.value ~default:Unknown (Names.find_opt name values)) (List.rev rev_offset) in
        charge value; value
    | Composite (kind, (_, items, _)) -> Sequence (kind, bounded_map eval 64 items)
    | Cast (_, value) -> eval value
    | Operator (op, args) ->
        let args = bounded_map (function IL.Unnamed value -> IL.Unnamed (expression (eval value))
          | IL.Named (name, value) -> IL.Named (name, expression (eval value))
          | IL.KeywordSpread value -> IL.KeywordSpread (expression (eval value))) 64 args in
        primitive IL.{ e = Operator (op, args); eorig = NoOrig }
    | _ -> Unknown
  in
  try evaluate depth expr with Value_limit -> Unknown

let bind lang ~before name expr values =
  match evaluate lang before 0 expr with
  | Unknown -> Names.remove name values
  | value when Names.cardinal values < 128 || Names.mem name values -> Names.add name value values
  | _ -> values

let transfer lang ~before instr values =
  let clear_result () = match IL_helpers.lval_of_instr_opt instr with
      | Some { base = Var name; _ } -> Names.remove name values
      | _ -> values in
  match lang, instr.IL.i with
  | Lang.Dart, Assign ({ base = Var name; rev_offset = [] }, expr)
    when Tok.is_fake (snd name.ident) ->
      (* Generated temporaries cannot be reassigned by a source-level closure.
       * Retain only immutable literals, never mutable container snapshots. *)
      (match evaluate lang before 0 expr with
      | Literal _ -> bind lang ~before name expr values
      | _ -> Names.remove name values)
  | Lang.Dart, _ -> clear_result ()
  | Lang.Clojure, Assign ({ base = Var name; rev_offset = [] }, expr)
    when not (Names.is_empty before) -> bind lang ~before name expr values
  | Lang.Clojure, _ when not (Names.is_empty before) -> clear_result ()
  | _ -> values

let eval_bool lang values expr =
  if Names.is_empty values then None
  else evaluate lang values 0 expr |> expression
    |> Eval_il_partial.eval_bool (Eval_il_partial.mk_env lang Dataflow_var_env.VarMap.empty)
