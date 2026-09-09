let diagnostics = Domain.DLS.new_key (fun () -> ref [])
let reset_diagnostics () = Domain.DLS.set diagnostics (ref [])

let take_diagnostics () =
  let items = Domain.DLS.get diagnostics in
  let result = !items in
  items := [];
  result

let gap kind origin =
  match AST_generic_helpers.range_of_any_opt (IL.any_of_orig origin) with
  | None -> ()
  | Some (location, _) ->
      let items = Domain.DLS.get diagnostics in
      let item = (kind, Some location) in
      if List.length !items < 16 && not (List.mem item !items) then
        items := item :: !items

let sink location shape =
  let module S = Shape_and_sig.Shape in
  let remaining = ref 1024 in
  let rec unknown depth shape =
    decr remaining;
    if depth > 32 || !remaining < 0 then false
    else
      match shape with
      | S.Exceptions alternatives ->
          List.exists (fun (kind, value) ->
            kind = S.UnknownException || cell (depth + 1) value) alternatives
      | S.Instance (_, fields) | S.Array {fields; _} | S.TemplateArray {fields; _} | S.Obj fields ->
          Shape_and_sig.Fields.exists (fun _ value -> cell (depth + 1) value) fields
      | S.Mapping choices ->
          List.exists (List.exists (function
            | S.Copy value -> cell (depth + 1) value
            | S.Remove _ -> false)) choices
      | S.Projection (value, _) -> cell (depth + 1) value
      | S.Bot | S.Scalar _ | S.Arg _ | S.Callable _ -> false
  and cell depth (S.Cell (_, shape)) = unknown depth shape in
  if unknown 0 shape then (
    let items = Domain.DLS.get diagnostics in
    let item = ("unknown_exception_value", Some location) in
    if List.length !items < 16 && not (List.mem item !items) then
      items := item :: !items)

let accepts expected = function
  | Shape_and_sig.Shape.KnownException actual when expected <> [] ->
      Some (List.exists (Python_exceptions.is_subclass actual) expected)
  | _ -> None

let refine ~lang ~truth expression env =
  match expression.IL.e with
  | ExceptionTypeIs ({ e = Fetch value; _ }, expected) -> (
      match Taint_lval_env.find_lval lang env value with
      | Some (Shape_and_sig.Shape.Cell (outer, Exceptions alternatives)) ->
          let remaining =
            List.filter
              (fun (name, _) ->
                match accepts expected name with
                | None -> true
                | Some matches -> Bool.equal matches truth)
              alternatives
          in
          if remaining = [] then Taint_lval_env.mark_dead env
          else
            let alternatives =
              List.map
                (fun (name, Shape_and_sig.Shape.Cell (taints, shape)) ->
                  ( name,
                    Shape_and_sig.Shape.Cell (Xtaint.union outer taints, shape)
                  ))
                remaining
            in
            Taint_lval_env.add_lval_shape lang value Taint.Taint_set.empty
              (Shape_and_sig.Shape.Exceptions alternatives)
              (Taint_lval_env.clean lang env value)
      | _ -> env)
  | _ -> env

let matches ~lang ~lookup expression =
  match expression.IL.e with
  | ExceptionTypeIs ({ e = Fetch value; _ }, expected) -> (
      match lookup lang value with
      | Some (Shape_and_sig.Shape.Cell (_, Exceptions alternatives)) -> (
          if
            List.exists
              (fun (name, cell) ->
                Option.is_none (accepts expected name)
                && not
                     (Taint.Taint_set.is_empty
                        (Taint_shape.gather_all_taints_in_cell cell)))
              alternatives
          then gap "exception_type_dispatch" expression.eorig;
          let decisions =
            List.map (fun (name, _) -> accepts expected name) alternatives
          in
          match decisions with
          | Some first :: rest
            when List.for_all (Option.equal Bool.equal (Some first)) rest ->
              Some first
          | _ -> None)
      | Some (Shape_and_sig.Shape.Cell (taints, shape)) ->
          if
            Taint_shape.taints_and_shape_are_relevant (Xtaint.to_taints taints)
              shape
          then gap "exception_type_dispatch" expression.eorig;
          None
      | None -> None)
  | _ -> None
