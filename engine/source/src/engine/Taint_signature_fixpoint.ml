module S = Shape_and_sig
module G = Call_graph.G

let diagnostics = Domain.DLS.new_key (fun () -> ref [])
let reset_diagnostics () = Domain.DLS.get diagnostics := []

let take_diagnostics () =
  let stored = Domain.DLS.get diagnostics in
  let result = !stored in
  stored := [];
  result

let record_limit node =
  let stored = Domain.DLS.get diagnostics in
  let location = Result.to_option (Tok.loc_of_tok (Function_id.tok node)) in
  let diagnostic = ("recursive_signature_limit", location) in
  if not (List.mem diagnostic !stored) then stored := diagnostic :: !stored

let ordered_components graph =
  let components = Call_graph.SCC.scc_list graph in
  let representatives, members =
    List.fold_left
      (fun (representatives, members) component ->
        match List.sort Function_id.compare component with
        | [] -> (representatives, members)
        | representative :: _ as component ->
            ( List.fold_left
                (fun map node -> S.FunctionMap.add node representative map)
                representatives component,
              S.FunctionMap.add representative component members ))
      (S.FunctionMap.empty, S.FunctionMap.empty)
      components
  in
  let condensed = G.create () in
  S.FunctionMap.iter
    (fun representative _ -> G.add_vertex condensed representative)
    members;
  G.iter_edges_e
    (fun edge ->
      let source = S.FunctionMap.find (G.E.src edge) representatives in
      let target = S.FunctionMap.find (G.E.dst edge) representatives in
      if not (Function_id.equal source target) then
        G.add_edge_e condensed (G.E.create source (G.E.label edge) target))
    graph;
  Call_graph.Topo.fold
    (fun representative reversed ->
      S.FunctionMap.find representative members :: reversed)
    condensed []
  |> List.rev

let equal_signatures left right =
  S.SignatureSet.cardinal left = S.SignatureSet.cardinal right
  && S.SignatureSet.for_all
       (fun (left : S.extended_sig) ->
         S.SignatureSet.exists
           (fun (right : S.extended_sig) ->
             S.equal_sig_arity left.arity right.arity
             && S.Signature.equal_with_guards left.sig_ right.sig_)
           right)
       left

let equal_component component (left : S.signature_database)
    (right : S.signature_database) =
  List.for_all
    (fun node ->
      match
        ( S.FunctionMap.find_opt node left.signatures,
          S.FunctionMap.find_opt node right.signatures )
      with
      | None, None -> true
      | Some left, Some right -> equal_signatures left right
      | _ -> false)
    component

let replace_signature node signature (database : S.signature_database) =
  let current =
    Option.value ~default:S.SignatureSet.empty
      (S.FunctionMap.find_opt node database.signatures)
  in
  let retained =
    S.SignatureSet.filter
      (fun (prior : S.extended_sig) ->
        not (S.equal_sig_arity prior.arity signature.S.arity))
      current
  in
  {
    database with
    signatures =
      S.FunctionMap.add node
        (S.SignatureSet.add signature retained)
        database.signatures;
  }

let run ~graph ~seed ~step initial =
  let components = ordered_components graph in
  List.fold_left
    (fun database component ->
      let recursive =
        match component with
        | [ node ] -> G.mem_edge graph node node
        | _ :: _ :: _ -> true
        | _ -> false
      in
      if not recursive then
        List.fold_left (fun db node -> step node db) database component
      else
        let initial =
          List.fold_left (fun db node -> seed node db) database component
        in
        let rec converge rounds database =
          let updated =
            List.fold_left (fun db node -> step node db) database component
          in
          if equal_component component database updated then updated
          else if rounds = 64 then (
            List.iter record_limit component;
            updated)
          else converge (rounds + 1) updated
        in
        converge 1 initial)
    initial components
