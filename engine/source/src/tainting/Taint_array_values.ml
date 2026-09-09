module S = Shape_and_sig.Shape
module Fields = Shape_and_sig.Fields
module Env = Taint_lval_env
module Taints = Taint.Taint_set

type operation = Push | Unshift
type call = { target : IL.lval; value : S.array_value; taints : Taints.t; operation : operation }

let property_name = function
  | Taint.Ofld name -> Some (fst name.IL.ident)
  | Taint.Ostr name -> Some name
  | _ -> None

let resolve lang env (callee : IL.exp) =
  if not (Lang.is_js lang) then None
  else match callee.e with
    | IL.Fetch ({rev_offset = method_offset :: parent; _} as target) ->
        let method_name = match Taint.offset_of_rev_IL_offset lang ~rev_offset:[method_offset] with
          | [offset] -> property_name offset
          | _ -> None in
        let operation = match method_name with
          | Some "push" -> Some Push | Some "unshift" -> Some Unshift | _ -> None in
        let target = {target with rev_offset = parent} in
        (match operation, Env.find_lval lang env target with
        | Some operation, Some (S.Cell (taints, S.Array value))
          when not (Fields.mem Taint.Oany value.fields)
            && not (Fields.exists (fun offset _ -> Option.equal String.equal (property_name offset) method_name) value.fields) ->
              Some {target; value; taints = Xtaint.to_taints taints; operation}
        | _ -> None)
    | _ -> None

let cell (taints, shape) =
  S.Cell ((if Taints.is_empty taints then `Clean else Xtaint.of_taints taints), shape)

let join_at key incoming fields =
  Fields.update key (fun prior -> Some (match prior with
    | None -> incoming | Some prior -> Taint_shape.unify_cell prior incoming)) fields

let append_unknown first incoming fields =
  let fields = Fields.mapi (fun key prior -> match key with
    | Taint.Oint index when index >= first -> Taint_shape.unify_cell prior incoming
    | Taint.Oslice start when start >= first -> Taint_shape.unify_cell prior incoming
    | _ -> prior) fields in
  join_at (Taint.Oslice first) incoming fields

let bounded_fields origin fields =
  let start = function Taint.Oint index | Taint.Oslice index -> Some index | _ -> None in
  let positions = Fields.bindings fields |> List.filter (fun (key, _) -> Option.is_some (start key))
    |> List.sort (fun (left, _) (right, _) -> Option.compare Int.compare (start left) (start right)) in
  if List.length positions <= Limits_semgrep.taint_MAX_SEQUENCE_FIELDS then fields
  else (
    Taint_model_types.array_shape_limit origin;
    let rec split remaining kept = function
      | [] -> (List.rev kept, [])
      | rest when Int.equal remaining 0 -> (List.rev kept, rest)
      | first :: rest -> split (remaining - 1) (first :: kept) rest in
    let kept, dropped = split (Limits_semgrep.taint_MAX_SEQUENCE_FIELDS - 1) [] positions in
    let fields = Fields.filter (fun key _ -> Option.is_none (start key)) fields in
    let fields = List.fold_left (fun fields (key, value) -> Fields.add key value fields) fields kept in
    match dropped with
    | [] -> fields
    | (key, first) :: rest ->
        let first_index = Option.value ~default:0 (start key) in
        let summary = List.fold_left (fun prior (_, value) -> Taint_shape.unify_cell prior value) first rest in
        append_unknown first_index summary fields)

let append_sequence ~origin (left : S.array_value) (right : S.array_value) =
  let fields = Fields.fold (fun key value fields ->
    match key, Sequence_length.exact_value left.length with
    | Taint.Oint index, Some first when index >= 0 && index < 4_294_967_295 -> Fields.add (Taint.Oint (first + index)) value fields
    | Taint.Oslice start, Some first -> append_unknown (first + start) value fields
    | Taint.Oint index, None when index >= 0 && index < 4_294_967_295 -> append_unknown (left.length.minimum + index) value fields
    | Taint.Oslice start, None -> append_unknown (left.length.minimum + start) value fields
    | _ -> fields) right.fields left.fields in
  S.{fields = bounded_fields origin fields; length = Sequence_length.concat left.length right.length}

let iterable (taints, shape) =
  match shape with
  | (S.Array value | S.TemplateArray value) when Fields.mem Taint.Oany value.fields ->
      let taints = Taints.union taints (Taint_shape.gather_all_taints_in_shape shape) in
      S.{fields = Fields.singleton (Taint.Oslice 0) (cell (taints, S.Bot)); length = Sequence_length.unknown}
  | S.Array value | S.TemplateArray value ->
      let fields = Fields.filter (fun key _ -> match key with
        | Taint.Oint index -> index >= 0 && index < 4_294_967_295
        | Taint.Oslice _ | Taint.Oany -> true | _ -> false) value.fields in
      let fields = if Taints.is_empty taints then fields
        else append_unknown 0 (cell (taints, S.Bot)) fields in
      {value with fields}
  | _ ->
      let taints = Taints.union taints (Taint_shape.gather_all_taints_in_shape shape) in
      S.{fields = Fields.singleton (Taint.Oslice 0) (cell (taints, S.Bot)); length = Sequence_length.unknown}

let of_elements ~origin expressions values =
  List.fold_left2 (fun result expression value ->
    let incoming = if Taint_array_expression.is_spread expression then iterable value
      else S.{fields = Fields.singleton (Taint.Oint 0) (cell value); length = Sequence_length.exact 1} in
    append_sequence ~origin result incoming)
    S.{fields = Fields.empty; length = Sequence_length.exact 0} expressions values

let offset_lval target offset =
  {target with IL.rev_offset = Option.value ~default:[]
      (Taint.rev_IL_offset_of_offset [offset]) @ target.IL.rev_offset}


let positional = function
  | Taint.Oint index -> index >= 0 && index < 4_294_967_295
  | Taint.Oslice _ | Taint.Oany -> true
  | _ -> false

let attach_arguments ~before ~change lang env call expressions values =
  let start = match call.operation with Push -> call.value.length | Unshift -> Sequence_length.exact 0 in
  let destination index element = match Sequence_length.exact_value index with
    | Some first -> Taint.Oint (first + element)
    | None -> Taint.Oslice (index.minimum + element) in
  let attach env index element source shape = match shape with
    | S.Scalar _ | S.Callable _ -> env
    | _ -> Env.copy_array_element ~before ~array:call.target ~change lang env
        (offset_lval call.target (destination index element)) source in
  snd (List.fold_left2 (fun (index, env) expression value ->
    if Taint_array_expression.is_spread expression then
      let incoming = iterable value in
      let env = match expression.IL.e with
        | IL.Fetch source -> Fields.fold (fun offset (S.Cell (_, shape)) env -> match offset with
            | Taint.Oint element when element >= 0 ->
                attach env index element (offset_lval source offset) shape
            | _ -> env) incoming.fields env
        | _ -> env in
      Sequence_length.concat index incoming.length, env
    else
      let env = match expression.IL.e with
        | IL.Fetch source -> attach env index 0 source (snd value)
        | _ -> env in
      Sequence_length.add index 1, env)
    (start, env) expressions values)

let apply ~origin ~expressions lang env call arguments =
  let before = env in
  let values = List.map (function IL.Unnamed value | IL.Named (_, value) | IL.KeywordSpread value -> value) arguments in
  let expressions = List.map IL_helpers.exp_of_arg expressions in
  let incoming = of_elements ~origin expressions values in
  let change = match call.operation with Push -> None | Unshift -> Some (Taint_aliases.Prepend incoming.length) in
  let env = Option.fold ~none:env ~some:(Env.reindex_array_references lang env call.target) change in
  let value = match call.operation with
    | Push -> append_sequence ~origin call.value incoming
    | Unshift ->
        let value = append_sequence ~origin incoming call.value in
        let fields = Fields.fold (fun key cell fields -> if positional key then fields else Fields.add key cell fields)
            call.value.fields value.fields in
        {value with fields} in
  let env = Env.clean lang env call.target |> Env.add_lval_shape lang call.target call.taints (S.Array value) in
  let env = attach_arguments ~before ~change lang env call expressions values in
  (Taints.empty, S.Bot, env)

let copy_spread_references ~before lang env target expression =
  match expression.IL.e with
  | IL.Composite (IL.CArray, _) ->
      Taint_references.assignment ~before lang env target expression
  | IL.Fetch source ->
      (match Env.find_lval lang before source with
      | Some (S.Cell (_, (S.Array value | S.TemplateArray value))) ->
          Fields.fold (fun offset (S.Cell (_, shape)) env ->
            match offset, shape with
            | Taint.Oint _, (S.Scalar _ | S.Callable _) -> env
            | Taint.Oint _, _ -> Env.copy_reference ~before ~replaced:target lang env
                (offset_lval target offset) (offset_lval source offset)
            | _ -> env) value.fields env
      | _ -> env)
  | _ -> env

let after_instruction ~before lang env (instruction : IL.instr) =
  if not (Lang.is_js lang) then env
  else match instruction.i with
    | IL.CallSpecial (Some target, (IL.SpreadFn, _), [IL.Unnamed expression]) ->
        copy_spread_references ~before lang env target expression
    | IL.Assign (({rev_offset = offset :: parent; _} as target), expression) ->
        let is_length = match Taint.offset_of_rev_IL_offset lang ~rev_offset:[offset] with
          | [offset] -> Option.equal String.equal (property_name offset) (Some "length")
          | _ -> false in
        let target = {target with rev_offset = parent} in
        (match is_length, Env.find_lval lang env target with
        | true, Some (S.Cell (taints, S.Array value)) ->
            let count = match Eval_il_partial.eval (Eval_il_partial.mk_env lang Dataflow_var_env.VarMap.empty) expression with
              | AST_generic.Lit (AST_generic.Int count) -> Parsed_int.to_int_opt count
              | AST_generic.Lit (AST_generic.Float (Some count, _))
                when Float.is_finite count && count >= 0. && count <= 4_294_967_295.
                  && Float.equal count (Float.floor count) -> Some (int_of_float count)
              | _ -> None in
            let length, fields = match count with
              | Some count when count >= 0 && count <= 4_294_967_295 ->
                  let fields = Fields.filter (fun offset _ -> match offset with
                    | Taint.Oint index -> index < count || index >= 4_294_967_295
                    | Taint.Oslice first -> first < count
                    | _ -> true) value.fields in
                  (Sequence_length.exact count, fields)
              | _ -> (Sequence_length.unknown, value.fields) in
            let count = (match count with Some count when count >= 0 && count <= 4_294_967_295 -> Some count | _ -> None) in
            let env = Env.reindex_array_references lang env target (Taint_aliases.Resize count) in
            Env.clean lang env target
            |> Env.add_lval_shape lang target (Xtaint.to_taints taints) (S.Array {fields; length})
        | _ -> env)
    | _ -> env
