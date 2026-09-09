module Env = Taint_lval_env

(* Escaping throws connect directly to Exit. Their side effects remain part of
   the all-completion mapping, but cannot initialize a successfully returned value. *)
let normal_env (cfg : IL.cfg) mapping =
  CFG.predecessors cfg cfg.exit
  |> List.fold_left
       (fun env (index, _) ->
         match (cfg.graph#nodes#find index).IL.n with
         | IL.NThrow _ -> env
         | _ when not (CFG.NodeiSet.mem index cfg.reachable) -> env
         | _ -> Env.union env mapping.(index).Dataflow_core.out_env)
       (Env.mark_dead Env.empty)

let exceptional_env (cfg : IL.cfg) mapping =
  CFG.predecessors cfg cfg.exit
  |> List.fold_left
       (fun env (index, _) ->
         match (cfg.graph#nodes#find index).IL.n with
         | IL.NThrow _ when CFG.NodeiSet.mem index cfg.reachable ->
             Env.union env mapping.(index).Dataflow_core.out_env
         | _ -> env)
       (Env.mark_dead Env.empty)

(* The original call has already applied callback models and side effects.
   Summary substitution only observes argument values. *)
let value_predicates (preds : Taint_rule_inst.spec_predicates) =
  Taint_rule_inst.
    {
      is_source =
        (fun value ->
          preds.is_source value
          |> List.filter_map
               (fun (matched : Rule.taint_source Taint_spec_match.t) ->
                 match
                   ( matched.spec.source_to_parameter,
                     matched.spec.source_by_side_effect )
                 with
                 | Some _, _ | _, Rule.Only -> None
                 | None, (Rule.No | Rule.Yes) ->
                     Some
                       {
                         matched with
                         spec =
                           { matched.spec with source_by_side_effect = Rule.No };
                       }));
      is_sanitizer =
        (fun value ->
          preds.is_sanitizer value
          |> List.filter
               (fun (matched : Rule.taint_sanitizer Taint_spec_match.t) ->
                 not matched.spec.sanitizer_by_side_effect));
      is_sink = (fun _ -> []);
      is_call_sink = (fun _ -> []);
      is_propagator = (fun _ -> []);
    }
