module S = Shape_and_sig.Shape
module Fields = Shape_and_sig.Fields
module Env = Taint_lval_env

let rec unknown_callbacks = function
  | S.TemplateArray _ as shape -> shape
  | S.Instance (_, fields)
  | S.Obj fields ->
      S.Obj
        (Fields.map
           (fun (S.Cell (taints, shape)) ->
             S.Cell (taints, unknown_callbacks shape))
           fields)
  | S.Array value ->
      let fields = Fields.map (fun (S.Cell (taints, shape)) -> S.Cell (taints, unknown_callbacks shape)) value.fields in
      S.Array {fields = Fields.add Taint.Oany (S.Cell (`None, S.Bot)) fields;
        length = Sequence_length.unknown}
  | _ -> S.Bot

let descendant target offset =
  {
    target with
    IL.rev_offset =
      Option.value ~default:[] (Taint.rev_IL_offset_of_offset [ offset ])
      @ target.IL.rev_offset;
  }

let invalidate env target =
  let rec walk env target = function
    | S.TemplateArray _ -> env
    | S.Array {fields; _} as shape ->
        let env =
          Fields.fold
            (fun offset (S.Cell (_, nested)) env ->
              walk env (descendant target offset) nested)
            fields env
        in
        let taints =
          match Env.find_lval_poly Lang.Js env target with
          | Some (taints, _) -> taints
          | None -> Taint.Taint_set.empty
        in
        Env.clean Lang.Js env target
        |> Env.add_lval_shape Lang.Js target taints (unknown_callbacks shape)
    | S.Instance (_, fields)
    | S.Obj fields ->
        Fields.fold
          (fun offset (S.Cell (_, shape)) env ->
            walk env (descendant target offset) shape)
          fields env
    | _ -> env
  in
  match Env.find_lval_poly Lang.Js env target with
  | Some (_, shape) -> walk env target shape
  | None -> env

let preserved_value preserved expression =
  match
    AST_generic_helpers.range_of_any_opt
      (IL.any_of_value_orig expression.IL.eorig)
  with
  | None -> false
  | Some (first, last) ->
      let range = Range.range_of_token_locations first last in
      List.exists (fun expected -> Range.equal expected range) preserved

let rec argument ~preserved env expression =
  if preserved_value preserved expression then env
  else
    match expression.IL.e with
    | IL.Fetch target -> invalidate env target
    | IL.Cast (_, expression) -> argument ~preserved env expression
    | IL.Composite (_, (_, elements, _)) ->
        List.fold_left (argument ~preserved) env elements
    | IL.RecordOrDict fields ->
        List.fold_left
          (fun env field ->
            match field with
            | IL.Field (_, value)
            | IL.Entry (_, value)
            | IL.Spread value ->
                argument ~preserved env value)
          env fields
    | _ -> env

let instruction ~preserved env instruction =
  match instruction.IL.i with
  | IL.Call (_, callee, arguments) ->
      let env =
        match callee.IL.e with
        | IL.Fetch ({ rev_offset = _method :: rest; _ } as target) ->
            invalidate env { target with rev_offset = rest }
        | _ -> env
      in
      List.fold_left
        (fun env argument_ ->
          argument ~preserved env (IL_helpers.exp_of_arg argument_))
        env arguments
  | _ -> env
