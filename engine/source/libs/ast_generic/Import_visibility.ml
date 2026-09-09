module G = AST_generic

type selector = Show of G.tok * G.ident list | Hide of G.tok * G.ident list

type t = {
  shown : string list option;
  hidden : string list;
  alternatives : string list;
  prefix : string;
}

let show_marker = "import_show"
let hide_marker = "import_hide"
let alternatives_marker = "import_alternatives"
let prefix_marker = "import_prefix"
let unrestricted = { shown = None; hidden = []; alternatives = []; prefix = "" }

let with_prefix tok prefix attributes =
  if prefix = "" then attributes
  else
    G.OtherAttribute ((prefix_marker, tok), [ G.I (prefix, tok) ]) :: attributes

let imported_symbol visibility local =
  if String.starts_with ~prefix:visibility.prefix local then
    Some
      (String.sub local
         (String.length visibility.prefix)
         (String.length local - String.length visibility.prefix))
  else None

let module_name = function
  | G.FileName (name, _) -> name
  | G.DottedName names -> String.concat "." (List.map fst names)

let attributes selectors alternatives =
  let selectors =
    List.map
      (fun selector ->
        let marker, tok, names =
          match selector with
          | Show (tok, names) -> (show_marker, tok, names)
          | Hide (tok, names) -> (hide_marker, tok, names)
        in
        G.OtherAttribute ((marker, tok), List.map (fun name -> G.I name) names))
      selectors
  in
  match alternatives with
  | [] -> selectors
  | (tok, _) :: _ ->
      selectors
      @ [
          G.OtherAttribute
            ( (alternatives_marker, tok),
              List.map (fun (_, name) -> G.Modn name) alternatives );
        ]

let of_attributes attributes =
  List.fold_left
    (fun visibility attribute ->
      match attribute with
      | G.OtherAttribute ((marker, _), values)
        when String.equal marker show_marker ->
          let names =
            List.filter_map
              (function
                | G.I (name, _) -> Some name
                | _ -> None)
              values
          in
          let shown =
            match visibility.shown with
            | None -> names
            | Some previous ->
                List.filter (fun name -> List.mem name names) previous
          in
          { visibility with shown = Some shown }
      | G.OtherAttribute ((marker, _), values)
        when String.equal marker hide_marker ->
          let names =
            List.filter_map
              (function
                | G.I (name, _) -> Some name
                | _ -> None)
              values
          in
          { visibility with hidden = names @ visibility.hidden }
      | G.OtherAttribute ((marker, _), values)
        when String.equal marker alternatives_marker ->
          let names =
            List.filter_map
              (function
                | G.Modn name -> Some (module_name name)
                | _ -> None)
              values
          in
          { visibility with alternatives = names @ visibility.alternatives }
      | G.OtherAttribute ((marker, _), [ G.I (prefix, _) ])
        when String.equal marker prefix_marker ->
          { visibility with prefix }
      | _ -> visibility)
    unrestricted attributes

let module_is_fixed visibility name =
  List.for_all (String.equal name) visibility.alternatives

let allows visibility name =
  Option.fold ~none:true ~some:(List.mem name) visibility.shown
  && not (List.mem name visibility.hidden)

let selected selectors =
  let visibility = of_attributes (attributes selectors []) in
  match visibility.shown with
  | None -> None
  | Some _ ->
      let names =
        List.concat_map
          (function
            | Show (_, names) -> names
            | Hide _ -> [])
          selectors
      in
      Some
        (names
        |> List.filter (fun (name, _) -> allows visibility name)
        |> List.sort_uniq (fun (left, _) (right, _) ->
            String.compare left right))
