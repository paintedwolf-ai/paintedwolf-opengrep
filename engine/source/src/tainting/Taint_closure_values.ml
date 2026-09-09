module S = Shape_and_sig.Shape

let from_lvals ~lookup values =
  let remaining = ref 4096 in
  let limited = ref false in
  let rec shape depth found value =
    decr remaining;
    if depth > 32 || !remaining < 0 then (
      limited := true;
      found)
    else
      match value with
      | S.Projection (cell, path) ->
          (match Taint_shape.find_in_cell path cell with
          | `Found (S.Cell (_, S.Projection _)) -> found
          | `Found (S.Cell (_, value)) -> shape (depth + 1) found value
          | `Clean | `Not_found _ -> found)
      | S.Mapping choices ->
          List.fold_left (List.fold_left (fun found -> function
            | S.Copy (S.Cell (_, value)) -> shape (depth + 1) found value
            | S.Remove _ -> found)) found choices
      | S.Callable targets -> IL.NameSet.union targets.closures found
      | S.Instance (_, fields) | (S.TemplateArray {fields; _} | S.Array {fields; _}) | S.Obj fields ->
          Shape_and_sig.Fields.fold
            (fun _ (S.Cell (_, value)) found -> shape (depth + 1) found value)
            fields found
      | S.Exceptions alternatives -> List.fold_left (fun found (_, S.Cell (_, value)) ->
          shape (depth + 1) found value) found alternatives
      | S.Scalar _ | S.Bot | S.Arg _ -> found
  in
  let names = List.fold_left
    (fun found value ->
      match lookup value with
      | Some (S.Cell (_, value)) -> shape 0 found value
      | None -> found)
    IL.NameSet.empty values
  in
  (names, !limited)

let escapes = function
  | IL.NInstr { i = IL.Assign ({ base = IL.Var _; rev_offset = [] }, _); _ }
  | IL.NInstr { i = IL.AssignAnon _; _ }
  | IL.NCond _ | IL.TrueNode _ | IL.FalseNode _ -> false
  | _ -> true

let read_values = function
  | IL.NInstr { i = IL.Assign (_, value); _ } -> IL_helpers.lvals_of_exp value
  | node -> IL_helpers.rlvals_of_node node
