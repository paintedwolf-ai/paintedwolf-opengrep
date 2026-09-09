module Taints = Taint.Taint_set
module Lval_env = Taint_lval_env

type origin =
  | Propagation of Dataflow_var_env.var
  | Source of Taints.t * Shape_and_sig.Shape.shape

type request = {
  closures : IL.NameSet.t;
  limitation : string option;
  value_range : Range.t;
  parameter : Rule.callback_parameter;
  origin : origin;
  location : Tok.location;
}

type input =
  IL.name
  * Rule.callback_parameter
  * Taints.t
  * Shape_and_sig.Shape.shape
  * Tok.location

let diagnostics = Domain.DLS.new_key (fun () -> ref [])
let reset_diagnostics () = Domain.DLS.set diagnostics (ref [])

let take_diagnostics () =
  let current = Domain.DLS.get diagnostics in
  let result = !current in
  current := [];
  result

let gap kind location =
  let current = Domain.DLS.get diagnostics in
  let item = (kind, Some location) in
  if List.length !current < 16 && not (List.mem item !current) then
    current := item :: !current

let targets parameter shape =
  let module S = Shape_and_sig.Shape in
  let remaining = ref 128 in
  let limitation = ref None in
  let mark kind =
    if !limitation <> Some "callback_array_limit" then limitation := Some kind
  in
  let rec visit depth names = function
    | _ when depth > 16 || !remaining <= 0 ->
        mark "callback_array_limit";
        names
    | shape -> (
        decr remaining;
        match shape with
        | S.Callable targets ->
            if not (S.has_complete_closure_targets targets) then mark "unresolved_callback";
            if IL.NameSet.is_empty targets.closures then mark "callback_body_unavailable";
            IL.NameSet.union names targets.closures
        | S.Scalar _ -> names
        | (S.TemplateArray {fields; _} | S.Array {fields; _}) when parameter.Rule.array_elements ->
            Shape_and_sig.Fields.fold
              (fun offset (S.Cell (_, element)) names ->
                match offset with
                | Taint.Oint _
                | Taint.Oany
                | Taint.Oslice _ ->
                    visit (depth + 1) names element
                | Taint.Ofld _
                | Taint.Oatom _
                | Taint.Ostr _ ->
                    names)
              fields names
        | _ ->
            mark "unresolved_callback";
            names)
  in
  let rec callable_head depth = function
    | _ when depth > 16 ->
        mark "callback_array_limit";
        None
    | S.Callable _ ->
        Some true
    | S.Scalar _ -> Some false
    | (S.TemplateArray {fields; length} | S.Array {fields; length}) -> (
        match Shape_and_sig.Fields.find_opt (Taint.Oint 0) fields with
        | Some (S.Cell (_, first)) -> callable_head (depth + 1) first
        | None when Option.equal Int.equal (Sequence_length.exact_value length) (Some 0) -> Some false
        | None when Shape_and_sig.Fields.is_empty fields -> Some false
        | None -> None)
    | _ -> None
  in
  let closures =
    if not parameter.Rule.array_head_callable then
      visit 0 IL.NameSet.empty shape
    else
      match callable_head 0 shape with
      | Some true -> visit 0 IL.NameSet.empty shape
      | Some false -> IL.NameSet.empty
      | None ->
          mark "unresolved_callback";
          IL.NameSet.empty
  in
  (closures, !limitation)

let preserved_arrays env requests =
  requests
  |> List.filter_map (fun request ->
      if not request.parameter.Rule.preserves_array then None
      else
        let taints =
          match request.origin with
          | Source (taints, _) -> Some taints
          | Propagation variable -> fst (Lval_env.propagate_from variable env)
        in
        match taints with
        | Some taints when not (Taints.is_empty taints) ->
            Some request.value_range
        | _ -> None)

let resolve env lambdas requests =
  let variables =
    requests
    |> List.filter_map (fun request ->
        match request.origin with
        | Propagation variable -> Some variable
        | Source _ -> None)
    |> List.sort_uniq String.compare
  in
  let env, incoming =
    List.fold_left
      (fun (env, values) variable ->
        let taints, env = Lval_env.propagate_from variable env in
        (env, (variable, taints) :: values))
      (env, []) variables
  in
  let inputs =
    requests
    |> List.concat_map (fun request ->
        let incoming =
          match request.origin with
          | Source (taints, _) -> Some taints
          | Propagation variable -> List.assoc variable incoming
        in
        match incoming with
        | Some taints when not (Taints.is_empty taints) ->
            Option.iter
              (fun kind -> gap kind request.location)
              request.limitation;
            request.closures |> IL.NameSet.elements
            |> List.filter_map (fun name ->
                if IL.NameMap.mem name lambdas then
                  let shape =
                    match request.origin with
                    | Source (_, shape) -> shape
                    | Propagation _ -> Shape_and_sig.Shape.Bot
                  in
                  Some (name, request.parameter, taints, shape, request.location)
                else (
                  gap "callback_body_unavailable" request.location;
                  None))
        | _ -> [])
  in
  (inputs, env)

let at_parameter token taints =
  match Tok.loc_of_tok token with
  | Error _ -> taints
  | Ok location ->
      Taints.map_taint
        (fun taint ->
          match taint.Taint.orig with
          | Taint.Src ({ call_trace = Taint.PM (pm, spec); _ } as source)
            when Option.is_some spec.Rule.source_to_parameter ->
              let pm =
                {
                  pm with
                  Core_match.range_loc = (location, location);
                  tokens = lazy [ token ];
                  ast_node = None;
                }
              in
              {
                Taint.orig =
                  Taint.Src { source with call_trace = Taint.PM (pm, spec) };
                tokens = [];
              }
          | _ -> taint)
        taints

let apply_parameter lang name path taints shape env =
  let taints, env =
    match
      ( shape,
        Lval_env.find_poly env name path,
        Taint.rev_IL_offset_of_offset path )
    with
    | ( (Shape_and_sig.Shape.Instance _ | Shape_and_sig.Shape.Scalar _),
        Some (existing, Shape_and_sig.Shape.Arg _),
        Some rev_offset ) ->
        (* A declared input type refines the generic argument placeholder. *)
        let lval = IL.{ base = Var name; rev_offset } in
        (Taints.union existing taints, Lval_env.clean lang env lval)
    | _ -> (taints, env)
  in
  Lval_env.add_shape name path taints shape env

type binding =
  IL.name * Taint.offset list * Taints.t * Shape_and_sig.Shape.shape

let add_parameter name path taints shape bindings : binding list =
  (name, path, taints, shape) :: bindings

let apply_bindings lang env bindings =
  let groups =
    List.fold_left
      (fun groups (name, path, taints, shape) ->
        let matching, others =
          List.partition
            (fun (other, offset, _, _) ->
              IL.equal_name name other
              && List.compare Taint.compare_offset path offset = 0)
            groups
        in
        let taints, shapes =
          List.fold_left
            (fun (taints, shapes) (_, _, prior, prior_shapes) ->
              (Taints.union taints prior, prior_shapes @ shapes))
            (taints, [ shape ]) matching
        in
        (name, path, taints, shapes) :: others)
      [] bindings
  in
  let groups =
    List.sort
      (fun (_, left, _, _) (_, right, _, _) ->
        Int.compare (List.length left) (List.length right))
      groups
  in
  List.fold_left
    (fun env (name, path, taints, shapes) ->
      let shapes =
        shapes
        |> List.filter (function
          | Shape_and_sig.Shape.Bot -> false
          | _ -> true)
        |> List.sort_uniq Shape_and_sig.Shape.compare_shape
      in
      let shape =
        match shapes with
        | [ shape ] -> shape
        | _ -> Shape_and_sig.Shape.Bot
      in
      apply_parameter lang name path taints shape env)
    env groups

let bind lang taints shape path id info env =
  let taints = at_parameter (snd id) taints in
  add_parameter
    (AST_to_IL.var_of_id_info id info)
    (List.map (Taint.model_field_offset lang) path)
    taints shape env

let property_name =
  let open AST_generic in
  function
  | EN (Id ((name, _), _)) -> Some name
  | EDynamic { e = L (String (_, (name, _), _)); _ } -> Some name
  | _ -> None

let rec expression lang location taints shape path value env =
  let open AST_generic in
  match value.e with
  | N (Id (id, info)) -> bind lang taints shape path id info env
  | Cast (_, _, value)
  | Assign (value, _, _) ->
      expression lang location taints shape path value env
  | Record (_, fields, _) ->
      let keys, unknown_key =
        List.fold_left
          (fun (keys, unknown) -> function
            | F { s = DefStmt ({ name; _ }, FieldDefColon _); _ } -> (
                match property_name name with
                | Some key -> (key :: keys, unknown)
                | None -> (keys, true))
            | _ -> (keys, unknown))
          ([], false) fields
      in
      List.fold_left
        (fun env field ->
          match field with
          | F
              {
                s =
                  DefStmt ({ name; _ }, FieldDefColon { vinit = Some value; _ });
                _;
              } -> (
              match (path, property_name name) with
              | [], _ ->
                  expression lang location taints Shape_and_sig.Shape.Bot []
                    value env
              | head :: rest, Some key when String.equal head key ->
                  expression lang location taints shape rest value env
              | _, None ->
                  gap "callback_parameter_binding" location;
                  env
              | _ -> env)
          | F
              {
                s =
                  ExprStmt
                    ( {
                        e =
                          Call
                            ( { e = IdSpecial (Spread, _); _ },
                              (_, [ Arg value ], _) );
                        _;
                      },
                      _ );
                _;
              } -> (
              match path with
              | head :: _ when List.mem head keys -> env
              | _ :: _ when unknown_key ->
                  gap "callback_parameter_binding" location;
                  env
              | [] ->
                  expression lang location taints Shape_and_sig.Shape.Bot []
                    value env
              | _ -> expression lang location taints shape path value env)
          | _ ->
              gap "callback_parameter_binding" location;
              env)
        env fields
  | _ ->
      gap "callback_parameter_binding" location;
      env

let rec pattern lang location taints shape path pat env =
  let open AST_generic in
  match pat with
  | PatId (id, info) -> bind lang taints shape path id info env
  | PatTyped (pat, _) -> pattern lang location taints shape path pat env
  | PatRecord (_, fields, _) ->
      List.fold_left
        (fun env (key, value) ->
          let rec project path key =
            match (path, key) with
            | [], _ -> Some []
            | rest, [] -> Some rest
            | head :: rest, (field, _) :: fields when String.equal head field ->
                project rest fields
            | _ -> None
          in
          match project path key with
          | Some rest ->
              let shape =
                if List.is_empty path then Shape_and_sig.Shape.Bot else shape
              in
              pattern lang location taints shape rest value env
          | None -> env)
        env fields
  | OtherPat (("ExprToPattern", _), [ E value ]) ->
      expression lang location taints shape path value env
  | _ ->
      gap "callback_parameter_binding" location;
      env

let arity lang params =
  let params = List.filter (function IL.ParamAll _ -> false | _ -> true) params in
  let rec required count = function
    | IL.Param { pdefault = Some _; _ } :: _
    | IL.ParamKeywordRest _ :: _
    | IL.ParamRest _ :: _
    | IL.ParamPattern ({ pdefault = Some _; _ }, _) :: _ ->
        count
    | IL.ParamPattern
        ( _,
          AST_generic.OtherPat
            ( ("ExprToPattern", _),
              [ AST_generic.E { e = AST_generic.Assign _; _ } ] ) )
      :: _ ->
        count
    | _ :: rest -> required (count + 1) rest
    | [] -> count
  in
  if Lang.is_js lang then required 0 params else List.length params

let seed_positional lang name params inputs env =
  List.fold_left
    (fun env (closure, target, taints, shape, location) ->
      if
        (not (IL.equal_name name closure))
        ||
        match target.Rule.arities with
        | Some arities -> not (List.mem (arity lang params) arities)
        | None -> false
      then env
      else
        let rec positional index = function
          | IL.ParamKeywordRest _ :: rest -> positional index rest
          | IL.ParamRest { pname; _ } :: _ ->
              let taints = at_parameter (snd pname.ident) taints in
              add_parameter pname
                (Taint.Oint index
                :: List.map (Taint.model_field_offset lang) target.path)
                taints shape env
          | _ :: rest when index > 0 -> positional (index - 1) rest
          | IL.Param { pname; _ } :: _ ->
              let taints = at_parameter (snd pname.ident) taints in
              add_parameter pname
                (List.map (Taint.model_field_offset lang) target.path)
                taints shape env
          | IL.ParamPattern (_, pat) :: _ ->
              pattern lang location taints shape target.path pat env
          | IL.ParamAll _ :: _
          | IL.ParamFixme :: _ ->
              gap "callback_parameter_binding" location;
              env
          | [] -> env
        in
        let captures = List.concat_map (function
            | IL.ParamAll { pname; _ } ->
                add_parameter pname
                  (Taint.Oint target.index :: List.map (Taint.model_field_offset lang) target.path)
                  (at_parameter (snd pname.ident) taints) shape env
            | _ -> []) params in
        captures @ positional target.index
          (List.filter (function IL.ParamAll _ -> false | _ -> true) params))
    [] inputs
  |> apply_bindings lang env

let seed_clojure name params inputs env =
  let inputs =
    List.filter (fun (closure, _, _, _, _) -> IL.equal_name name closure) inputs
  in
  match (inputs, params) with
  | [], _ -> [ env ]
  | _, [ IL.Param { pname; _ } ] ->
      let counts =
        inputs
        |> List.concat_map (fun (_, target, _, _, _) ->
            match target.Rule.arities with
            | None -> [ None ]
            | Some counts -> List.map Option.some counts)
        |> List.sort_uniq (Option.compare Int.compare)
      in
      List.map
        (fun count ->
          let env =
            Option.fold ~none:env
              ~some:(fun count -> Lval_env.set_sequence_length pname count env)
              count
          in
          List.fold_left
            (fun env (_, target, taints, shape, _) ->
              let applies =
                match (count, target.Rule.arities) with
                | None, None
                | Some _, None ->
                    true
                | Some count, Some counts ->
                    List.mem count counts && target.index < count
                | None, Some _ -> false
              in
              if not applies then env
              else
                add_parameter pname
                  (Taint.Oint target.index
                  :: List.map
                       (Taint.model_field_offset Lang.Clojure)
                       target.path)
                  taints shape env)
            [] inputs
          |> apply_bindings Lang.Clojure env)
        counts
  | _ ->
      List.iter
        (fun (_, _, _, _, location) ->
          gap "callback_parameter_binding" location)
        inputs;
      [ env ]

let seed lang name params inputs env =
  if Lang.equal lang Lang.Clojure then seed_clojure name params inputs env
  else [ seed_positional lang name params inputs env ]
