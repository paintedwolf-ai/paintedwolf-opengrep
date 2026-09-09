open IL
module G = AST_generic

type binding = { parameter : IL.param; actual : IL.exp }
type t = { bindings : binding list; args : IL.exp IL.argument list }
type resolution = Call of t | Invalid | Unsupported

let supports lang =
  Lang.is_js lang || Lang.equal lang Lang.Scheme || Lang.equal lang Lang.Clojure || Lang.equal lang Lang.Swift

let undefined token = { e = Literal (G.Undefined token); eorig = NoOrig }

let sequence kind token values =
  { e = Composite (kind, (token, values, token)); eorig = NoOrig }

let token_of_parameter = function
  | Param { pname; _ } | ParamRest { pname; _ } | ParamKeywordRest { pname; _ } | ParamAll { pname; _ }
  | ParamPattern ({ pname; _ }, _) -> snd pname.ident
  | ParamFixme -> Tok.unsafe_fake_tok "parameter"

let guard_actual lang prior binding =
  match binding.parameter with
  | Param { pname; pdefault = Some value }
  | ParamPattern ({ pname; pdefault = Some value }, _) ->
      let unresolved () = { e = Fetch (IL_helpers.lval_of_var pname); eorig = NoOrig } in
      let evaluated = Eval_il_partial.eval
        (Eval_il_partial.mk_env lang Dataflow_var_env.VarMap.empty) binding.actual in
      (match evaluated with
      | G.Lit (G.Undefined _) ->
          (match value.G.e with
          | G.L literal -> { e = Literal literal; eorig = ValueOf value }
          | G.N (G.Id (id, info)) ->
              let name = AST_to_IL.var_of_id_info id info in
              (match List.find_opt (fun (other, _) -> IL.equal_name name other) prior with
              | Some (_, actual) -> actual
              | None -> { e = Fetch (IL_helpers.lval_of_var name); eorig = ValueOf value })
          | _ -> unresolved ())
      | G.Cst _ | G.Sym _ | G.NotCst -> unresolved ()
      | _ -> binding.actual)
  | _ -> binding.actual

let positional_call lang bindings =
  let _, args = List.fold_left (fun (prior, args) binding ->
    match binding.parameter, binding.actual.e with
    | ParamAll _, _ -> (prior, args)
    | ParamRest _, Composite (_, (_, values, _)) ->
        (prior, args @ List.map (fun value -> Unnamed value) values)
    | _ ->
        let actual = guard_actual lang prior binding in
        let prior = match binding.parameter with
          | Param { pname; _ } | ParamPattern ({ pname; _ }, _) -> (pname, actual) :: prior
          | _ -> prior in
        (prior, args @ [ Unnamed actual ])) ([], []) bindings in
  Call { bindings; args }

let resolve_python params args =
  if List.exists (function KeywordSpread _ -> true | _ -> false) args then Unsupported
  else
    let positional = List.filter_map (function Unnamed value -> Some value | _ -> None) args in
    let named = List.filter_map (function Named (name, value) -> Some (fst name, value) | _ -> None) args in
    let rec bind bindings positional named = function
      | [] -> if List.is_empty positional && List.is_empty named then
          Call {bindings = List.rev bindings; args} else Invalid
      | (Param {pname; pdefault} as parameter) :: rest ->
          let matches, named = List.partition (fun (name, _) -> String.equal name (fst pname.ident)) named in
          (match positional, matches with
          | actual :: positional, [] -> bind ({parameter; actual} :: bindings) positional named rest
          | [], [(_, actual)] -> bind ({parameter; actual} :: bindings) [] named rest
          | [], [] when Option.is_some pdefault -> Unsupported
          | _ -> Invalid)
      | (ParamRest _ as parameter) :: rest ->
          bind ({parameter; actual = sequence CTuple (token_of_parameter parameter) positional} :: bindings) [] named rest
      | _ -> Unsupported
    in
    bind [] positional named params

let resolve lang params args =
  if Lang.equal lang Lang.Python then resolve_python params args
  else   if not (supports lang) then
    if List.is_empty params && List.is_empty args then Call { bindings = []; args = [] }
    else Unsupported
  else if List.exists (function Named _ | KeywordSpread _ -> true | Unnamed _ -> false) args then
    Unsupported
  else
    let values = List.map IL_helpers.exp_of_arg args in
    let all_params, params = List.partition (function ParamAll _ -> true | _ -> false) params in
    let finish bindings =
      match positional_call lang bindings with
      | Call call ->
          let captures = List.map (fun parameter ->
              { parameter; actual = sequence CArray (token_of_parameter parameter) values }) all_params in
          Call { bindings = captures @ call.bindings;
                 args = if List.is_empty all_params then call.args else args }
      | result -> result in
    if Lang.equal lang Lang.Swift then
      if List.exists (function Param { pdefault = None; _ } -> false | _ -> true) params then Unsupported
      else if not (Int.equal (List.length params) (List.length values)) then Invalid
      else positional_call lang (List.map2 (fun parameter actual -> { parameter; actual }) params values)
    else if Lang.equal lang Lang.Clojure then
      match params, values with
      | [ (Param _ as parameter) ], [actual] ->
          Call { bindings = [ { parameter; actual } ]; args }
      | _ -> Unsupported
    else
      let rec bind params values acc =
        match params, values with
        | [], [] -> finish (List.rev acc)
        | [], _ when Lang.is_js lang -> finish (List.rev acc)
        | [], _ -> Invalid
        | (ParamRest _ as parameter) :: [], values ->
            let kind = if Lang.is_js lang then CArray else CList in
            let actual = sequence kind (token_of_parameter parameter) values in
            finish (List.rev ({ parameter; actual } :: acc))
        | ParamRest _ :: _, _ | ParamAll _ :: _, _ | ParamKeywordRest _ :: _, _ | ParamFixme :: _, _ -> Unsupported
        | parameter :: rest, actual :: values ->
            bind rest values ({ parameter; actual } :: acc)
        | ((Param { pdefault; _ } | ParamPattern ({ pdefault; _ }, _)) as parameter) :: rest, [] ->
            if Lang.is_js lang || Option.is_some pdefault then
              bind rest [] ({ parameter; actual = undefined (token_of_parameter parameter) } :: acc)
            else Invalid
      in
      bind params values []

let default = function
  | Param { pdefault; _ } | ParamRest { pdefault; _ } | ParamKeywordRest { pdefault; _ } | ParamAll { pdefault; _ }
  | ParamPattern ({ pdefault; _ }, _) -> pdefault
  | ParamFixme -> None

let name = function
  | Param { pname; _ } | ParamRest { pname; _ } | ParamKeywordRest { pname; _ } | ParamAll { pname; _ }
  | ParamPattern ({ pname; _ }, _) -> Some pname
  | ParamFixme -> None

let default_statements lang parameter actual =
  match name parameter, default parameter with
  | Some pname, Some value ->
      let token = snd pname.ident in
      let target = G.N (G.Id (pname.ident, pname.id_info)) |> G.e in
      let assignment = G.Assign (target, token, value) |> G.e in
      let body = AST_to_IL.stmt lang (G.ExprStmt (assignment, token) |> G.s) in
      let condition =
        { e = Operator ((G.PhysEq, token), [ Unnamed actual; Unnamed (undefined token) ]);
          eorig = NoOrig }
      in
      [ { s = If (token, condition, body, []) } ]
  | _ -> []
