module G = AST_generic
module N = Tree_sitter_bindings.Tree_sitter_output_t
module T = Native_script_tree
module R = Scheme_reader

let module_name env node =
  if node.N.type_ <> "list" then None
  else
    let parts = T.code_children node in
    let names = List.filter_map (R.identifier env) parts in
    if names <> [] && List.length names = List.length parts then
      Some
        (G.FileName
           ( "("
             ^ String.concat " "
                 (List.map (fun (name, _) -> R.render_symbol name) names)
             ^ ")",
             T.token env node ))
    else None

let import env node =
  let tok = T.token env node in
  let directive attributes value =
    G.DirectiveStmt { G.d = value; d_attrs = attributes } |> G.s
  in
  let simple module_ = directive [] (G.ImportAll (tok, module_, tok)) in
  match T.code_children node with
  | first :: options when first.N.type_ = "list" -> (
      match module_name env first with
      | None -> [ G.exprstmt (T.unsupported env node) ]
      | Some module_ -> (
          let rec parse selected hidden prefix = function
            | [] -> Some (selected, hidden, prefix)
            | key :: value :: rest -> (
                match (T.text env key, value.N.type_) with
                | "#:select", "list" when Option.is_none selected ->
                    let entries = T.code_children value in
                    let entry item =
                      match R.identifier env item with
                      | Some id -> Some (id, id)
                      | None -> (
                          match T.code_children item with
                          | [ original; dot; local ] when T.text env dot = "."
                            ->
                              Option.bind (R.identifier env original)
                                (fun original ->
                                  Option.map
                                    (fun local -> (original, local))
                                    (R.identifier env local))
                          | _ -> None)
                    in
                    let names = List.filter_map entry entries in
                    if List.length names <> List.length entries then None
                    else parse (Some names) hidden prefix rest
                | "#:hide", "list" ->
                    let entries = T.code_children value in
                    let names = List.filter_map (R.identifier env) entries in
                    if List.length names <> List.length entries then None
                    else parse selected (names @ hidden) prefix rest
                | "#:prefix", "symbol" when prefix = "" ->
                    Option.bind (R.symbol env value) (fun prefix ->
                        parse selected hidden prefix rest)
                | _ -> None)
            | _ -> None
          in
          match parse None [] "" options with
          | None -> [ G.exprstmt (T.unsupported env node) ]
          | Some (selected, hidden, prefix) -> (
              let attrs =
                Import_visibility.attributes
                  [ Import_visibility.Hide (tok, hidden) ]
                  []
              in
              match selected with
              | None ->
                  let attrs = Import_visibility.with_prefix tok prefix attrs in
                  [ directive attrs (G.ImportAll (tok, module_, tok)) ]
              | Some names ->
                  let names =
                    List.filter
                      (fun ((name, _), _) -> not (List.mem_assoc name hidden))
                      names
                  in
                  [
                    directive attrs
                      (G.ImportFrom
                         ( tok,
                           module_,
                           List.map
                             (fun (original, (local, token)) ->
                               ( original,
                                 Some
                                   ((prefix ^ local, token), G.empty_id_info ())
                               ))
                             names ));
                  ])))
  | _ -> (
      match module_name env node with
      | Some module_ -> [ simple module_ ]
      | None -> [ G.exprstmt (T.unsupported env node) ])
