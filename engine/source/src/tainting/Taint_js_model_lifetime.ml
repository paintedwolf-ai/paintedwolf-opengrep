module S = Shape_and_sig.Shape
module Fields = Shape_and_sig.Fields
module Env = Taint_lval_env

let descendant target offset =
  Option.map
    (fun suffix ->
      { target with IL.rev_offset = suffix @ target.IL.rev_offset })
    (Taint.rev_IL_offset_of_offset [ offset ])

let invalidate env target =
  let rec walk env target = function
    | S.Instance (name, fields) ->
        let env = children env target fields in
        let taints =
          match Env.find_lval_poly Lang.Js env target with
          | Some (taints, _) -> taints
          | None -> Taint.Taint_set.empty
        in
        let fields =
          match Env.find_lval Lang.Js env target with
          | Some (S.Cell (_, S.Instance (_, updated))) -> updated
          | _ -> fields
        in
        let fields = Fields.add Taint.Oany (S.Cell (`None, S.Bot)) fields in
        Env.clean Lang.Js env target
        |> Env.add_lval_shape Lang.Js target taints (S.Instance (name, fields))
    | (S.TemplateArray {fields; _} | S.Array {fields; _})
    | S.Obj fields ->
        children env target fields
    | _ -> env
  and children env target fields =
    Fields.fold
      (fun offset (S.Cell (_, shape)) env ->
        match descendant target offset with
        | Some target -> walk env target shape
        | None -> env)
      fields env
  in
  match Env.find_lval_poly Lang.Js env target with
  | Some (_, shape) -> walk env target shape
  | None -> env

let preserved_any preserved any =
  match AST_generic_helpers.range_of_any_opt any with
  | None -> false
  | Some (first, last) ->
      let range = Range.range_of_token_locations first last in
      List.exists (Range.equal range) preserved

let lval_origin = function
  | { IL.base = IL.Var { value_origin = Some value; _ }; rev_offset = [] } ->
      AST_generic.E value
  | { rev_offset = { oorig; _ } :: _; _ } -> IL.any_of_orig oorig
  | { base = IL.Var var; rev_offset = [] } -> AST_generic.Tk (snd var.ident)
  | { base = IL.VarSpecial (_, tok); rev_offset = [] } -> AST_generic.Tk tok
  | { base = IL.Mem expression; rev_offset = [] } ->
      IL.any_of_orig expression.eorig

let rec argument ~preserved env expression =
  if preserved_any preserved (IL.any_of_value_orig expression.IL.eorig) then env
  else
    match expression.IL.e with
    | IL.Fetch target -> invalidate env target
    | IL.Cast (_, inner) -> argument ~preserved env inner
    | IL.Composite (_, (_, values, _)) ->
        List.fold_left (argument ~preserved) env values
    | IL.RecordOrDict fields ->
        List.fold_left
          (fun env -> function
            | IL.Field (_, value)
            | IL.Entry (_, value)
            | IL.Spread value ->
                argument ~preserved env value)
          env fields
    | _ -> env

let inert_body (body : IL.fun_cfg) =
  List.for_all
    (function
      | IL.Param { pdefault = None; _ } -> true
      | _ -> false)
    body.params
  && IL.NameMap.is_empty body.lambdas
  && List.for_all
       (fun (_, node) ->
         match node.IL.n with
         | IL.Enter
         | IL.Exit
         | IL.Join
         | IL.NGoto _ ->
             true
         | IL.NReturn (_, { e = IL.Literal _; _ }) -> true
         | _ -> false)
       body.cfg.graph#nodes#tolist

let inert_call env lambdas callee =
  let closures =
    match callee.IL.e with
    | IL.Fetch target -> (
        match Env.find_lval Lang.Js env target with
        | Some (S.Cell (_, S.Callable targets)) when S.has_complete_closure_targets targets -> targets.closures
        | _ -> IL.NameSet.empty)
    | _ -> IL.NameSet.empty
  in
  (not (IL.NameSet.is_empty closures))
  && IL.NameSet.for_all
       (fun name ->
         Option.fold ~none:false ~some:inert_body
           (IL.NameMap.find_opt name lambdas))
       closures

let instruction ~preserved ~lambdas env instruction =
  match instruction.IL.i with
  | IL.Call (_, callee, arguments) when not (inert_call env lambdas callee) ->
      let env =
        match callee.IL.e with
        | IL.Fetch ({ rev_offset = _ :: rest; _ } as target) ->
            let receiver = { target with rev_offset = rest } in
            if preserved_any preserved (lval_origin receiver) then env
            else invalidate env receiver
        | _ -> env
      in
      List.fold_left
        (fun env value -> argument ~preserved env (IL_helpers.exp_of_arg value))
        env arguments
  | IL.New (_, _, _, arguments) ->
      List.fold_left
        (fun env value -> argument ~preserved env (IL_helpers.exp_of_arg value))
        env arguments
  | _ -> env
