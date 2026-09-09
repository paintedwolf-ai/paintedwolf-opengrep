module G = AST_generic
module S = Shape_and_sig.Shape
module Env = Taint_lval_env

let diagnostics : (string * Tok.location option) list ref Domain.DLS.key =
  Domain.DLS.new_key (fun () -> ref [])

let call_limit_diagnostics = Domain.DLS.new_key (fun () -> true)

let without_call_limit_diagnostics run =
  let previous = Domain.DLS.get call_limit_diagnostics in
  Domain.DLS.set call_limit_diagnostics false;
  Fun.protect ~finally:(fun () -> Domain.DLS.set call_limit_diagnostics previous) run

let shared_names = Domain.DLS.new_key (fun () -> Hashtbl.create 8)

let reset_diagnostics () =
  Domain.DLS.set diagnostics (ref []);
  Domain.DLS.set shared_names (Hashtbl.create 8)

let take_diagnostics () =
  let items = Domain.DLS.get diagnostics in
  let result = !items in
  items := [];
  result

let unresolved location =
  let items = Domain.DLS.get diagnostics in
  let item = ("model_type_unresolved", Some location) in
  if List.length !items < 16 && not (List.mem item !items) then
    items := item :: !items

let call_limit origin =
  if Domain.DLS.get call_limit_diagnostics then
  match AST_generic_helpers.range_of_any_opt (IL.any_of_orig origin) with
  | None -> ()
  | Some (location, _) ->
      let items = Domain.DLS.get diagnostics in
      let item = ("closure_call_limit", Some location) in
      if List.length !items < 16 && not (List.mem item !items) then
        items := item :: !items

let member_name bindings name =
  if not (Mvar.is_metavar_name name) then Some name
  else
    match List.assoc_opt name bindings with
    | Some value -> (
        match Metavariable.mvalue_to_any value with
        | G.E { e = G.N (G.Id ((name, _), _)); _ }
        | G.E { e = G.L (G.String (_, (name, _), _)); _ } ->
            Some name
        | _ -> None)
    | None -> None

let has_type bindings member name = function
  | S.Instance ((actual, _), fields) when String.equal name actual ->
      Option.fold ~none:true
        ~some:(fun member ->
          Option.fold ~none:false
            ~some:(fun name ->
              (not (Shape_and_sig.Fields.mem (Taint.Ostr name) fields))
              && not (Shape_and_sig.Fields.mem Taint.Oany fields))
            (member_name bindings member))
        member
  | _ -> false

let add_field lval offset =
  Option.map
    (fun offset -> { lval with IL.rev_offset = offset @ lval.IL.rev_offset })
    (Taint.rev_IL_offset_of_offset [ offset ])

let rec lval_of_expression value =
  match value.G.e with
  | G.N name -> Some (IL_helpers.lval_of_var (AST_to_IL.var_of_name name))
  | G.IdSpecial ((G.This | G.Super | G.Self | G.Parent) as receiver, token) ->
      let receiver =
        match receiver with
        | G.This -> IL.This
        | G.Super -> IL.Super
        | G.Self -> IL.Self
        | G.Parent -> IL.Parent
        | _ -> assert false
      in
      Some IL.{ base = VarSpecial (receiver, token); rev_offset = [] }
  | G.DotAccess (base, _, G.FN (G.Id (id, info))) ->
      Option.bind (lval_of_expression base) (fun lval ->
          add_field lval (Taint.Ofld (AST_to_IL.var_of_id_info id info)))
  | G.ArrayAccess (base, (_, { e = G.L (G.String (_, (key, _), _)); _ }, _)) ->
      Option.bind (lval_of_expression base) (fun lval ->
          add_field lval (Taint.Ostr key))
  | G.ArrayAccess (base, (_, { e = G.L (G.Int integer); _ }, _)) ->
      Option.bind (Parsed_int.to_int_opt integer) (fun index ->
          Option.bind (lval_of_expression base) (fun lval ->
              add_field lval (Taint.Oint index)))
  | G.ArrayAccess (base, (_, { e = G.L (G.Float (Some value, _)); _ }, _))
    when Float.is_finite value && Float.is_integer value
         && value >= float_of_int min_int
         && value < float_of_int max_int ->
      Option.bind (lval_of_expression base) (fun lval ->
          add_field lval (Taint.Oint (int_of_float value)))
  | G.OtherExpr (("DartNullAssert", _), [G.E inner])
  | G.Cast (_, _, inner) -> lval_of_expression inner
  | _ -> None

let from_model name = function
  | `Tainted taints ->
      List.exists
        (fun (guarded : Taint.guarded_taint) ->
          match guarded.taint.Taint.orig with
          | Taint.Src source ->
              let _, spec = Taint.pm_of_trace source.call_trace in
              spec.Rule.source_model_type = Some name
          | _ -> false)
        (Taint.Taint_set.elements taints)
  | _ -> false

let unresolved_member bindings member name fields =
  Option.fold ~none:false
    ~some:(fun member ->
      Option.fold ~none:false
        ~some:(fun member ->
          match Shape_and_sig.Fields.find_opt (Taint.Ostr member) fields with
          | Some (S.Cell (taints, S.Bot)) -> from_model name taints
          | _ -> false)
        (member_name bindings member))
    member

let constraint_holds ?(report_unresolved = true) lang env bindings = function
  | None -> true
  | Some (variable, name, member) -> (
      match List.assoc_opt variable bindings with
      | Some value -> (
          match Metavariable.mvalue_to_any value with
          | G.E expression -> (
              let cell =
                match lval_of_expression expression with
                | Some lval -> Env.find_lval lang env lval
                | None -> Env.find_value env expression
              in
              match cell with
              | Some (S.Cell (taints, shape)) ->
                  let holds = has_type bindings member name shape in
                  (if report_unresolved && (not holds) && from_model name taints then
                     match
                       ( shape,
                         AST_generic_helpers.range_of_any_opt (G.E expression)
                       )
                     with
                     | (S.Bot | S.Arg _ | S.Obj _), Some (location, _) ->
                         unresolved location
                     | S.Instance (_, fields), Some (location, _)
                       when Shape_and_sig.Fields.mem Taint.Oany fields
                            || unresolved_member bindings member name fields ->
                         unresolved location
                     | _ -> ());
                  holds
              | None -> false)
          | _ -> false)
      | None -> false)

let establish name ~singleton = function
  | S.Instance (_, fields)
  | S.Obj fields ->
      S.Instance ((name, singleton), fields)
  | _ -> S.Instance ((name, singleton), Shape_and_sig.Fields.empty)

let source_shape sources original =
  let sources = List.filter (fun source -> source.Rule.source_exact) sources in
  let models =
    sources
    |> List.filter_map (fun source ->
        Option.map
          (fun name -> (name, source.Rule.source_model_singleton))
          source.Rule.source_model_type)
    |> List.sort_uniq Stdlib.compare
  in
  let types =
    sources
    |> List.filter_map (fun source -> source.Rule.source_value_type)
    |> List.sort_uniq Rule.compare_taint_value_type
  in
  match (models, types) with
  | [], [] -> original
  | [ (name, singleton) ], [] -> establish name ~singleton original
  | [], [ kind ] -> S.Scalar kind
  | _ -> S.Bot

let shared_root name =
  let names = Domain.DLS.get shared_names in
  match Hashtbl.find_opt names name with
  | Some root -> root
  | None ->
      let root =
        IL.
          {
            ident =
              ("model-instance:" ^ name, Tok.unsafe_fake_tok "model-instance");
            sid = G.SId.mk ();
            id_info = G.empty_id_info ();
            value_origin = None;
          }
      in
      Hashtbl.add names name root;
      root

let is_shared_name value =
  Hashtbl.fold
    (fun _ name found -> found || IL.equal_name name value)
    (Domain.DLS.get shared_names)
    false

let share_value lang env target =
  match Env.find_lval lang env target with
  | Some (S.Cell (xtaint, (S.Instance ((name, true), _) as shape))) ->
      let taints = Xtaint.to_taints xtaint in
      let root = IL_helpers.lval_of_var (shared_root name) in
      let current = Env.find_lval lang env root in
      let env, taints, shape =
        match current with
        | Some (S.Cell (taints, shape)) -> (env, Xtaint.to_taints taints, shape)
        | None -> (Env.add_lval_shape lang root taints shape env, taints, shape)
      in
      let env, aliases = Env.prepare_assignment lang env target (Some root) in
      let env =
        Env.clean lang env target |> Env.add_lval_shape lang target taints shape
      in
      Env.finish_assignment env aliases
  | _ -> env

let immutable_template_write origin =
  match AST_generic_helpers.range_of_any_opt (IL.any_of_orig origin) with
  | None -> ()
  | Some (location, _) ->
      let items = Domain.DLS.get diagnostics in
      let item = ("immutable_template_write", Some location) in
      if List.length !items < 16 && not (List.mem item !items) then
        items := item :: !items

let array_shape_limit origin =
  match AST_generic_helpers.range_of_any_opt (IL.any_of_orig origin) with
  | None -> ()
  | Some (location, _) ->
      let items = Domain.DLS.get diagnostics in
      let item = ("array_shape_limit", Some location) in
      if List.length !items < 16 && not (List.mem item !items) then
        items := item :: !items
