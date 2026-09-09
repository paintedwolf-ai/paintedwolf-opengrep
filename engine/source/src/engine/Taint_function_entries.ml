module G = AST_generic
module S = Shape_and_sig

let escaped_bindings ast =
  let names = ref IL.NameSet.empty in
  let visitor =
    object (self)
      inherit [_] G.iter_no_id_info as super

      method! visit_expr () expression =
        match expression.G.e with
        | G.Call ({ e = G.N (G.Id _); _ }, (_, arguments, _)) ->
            List.iter (self#visit_argument ()) arguments
        | G.N (G.Id (id, info)) ->
            names := IL.NameSet.add (AST_to_IL.var_of_id_info id info) !names
        | _ -> super#visit_expr () expression
    end
  in
  visitor#visit_program () ast;
  !names

let root_functions graph =
  Taint_signature_fixpoint.ordered_components graph
  |> List.fold_left
       (fun roots component ->
         let members =
           List.fold_left
             (fun set node -> S.FunctionMap.add node () set)
             S.FunctionMap.empty component
         in
         let has_caller =
           List.exists
             (fun node ->
               Call_graph.G.succ graph node
               |> List.exists (fun caller ->
                   not (S.FunctionMap.mem caller members)))
             component
         in
         if has_caller then roots
         else
           List.fold_left
             (fun roots node -> S.FunctionMap.add node () roots)
             roots component)
       S.FunctionMap.empty

let standalone ~roots ~escaped name =
  S.FunctionMap.mem (Function_id.of_il_name name) roots
  || IL.NameSet.mem name escaped
