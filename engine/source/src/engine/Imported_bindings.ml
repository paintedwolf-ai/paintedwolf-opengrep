module G = AST_generic

type origin = {
  module_name : string;
  symbol : string list option;
  visibility : Import_visibility.t;
}

type t = {
  by_sid : (G.sid, origin) Hashtbl.t;
  unaliased : (string, origin option) Hashtbl.t;
  mutable wildcards : origin list;
  prefixes : (string, origin list) Hashtbl.t;
  invalidated_sids : (G.sid, unit) Hashtbl.t;
  invalidated_unbound : (string, unit) Hashtbl.t;
}

let module_name = Import_visibility.module_name

let of_program ?lang program =
  let bindings =
    {
      by_sid = Hashtbl.create 16;
      unaliased = Hashtbl.create 16;
      wildcards = [];
      prefixes = Hashtbl.create 8;
      invalidated_sids = Hashtbl.create 8;
      invalidated_unbound = Hashtbl.create 8;
    }
  in
  let record ?(visibility = Import_visibility.unrestricted) info name =
    match !(info.G.id_resolved) with
    | Some (G.ImportedModule canonical, sid) ->
        let module_name =
          if lang = Some Lang.Python then String.concat "." canonical else name in
        Hashtbl.replace bindings.by_sid sid
          { module_name; symbol = Some []; visibility }
    | Some (G.ImportedEntity canonical, sid) ->
        let symbol =
          match List.rev canonical with
          | [] -> None
          | last :: _ -> Some [ last ]
        in
        Hashtbl.replace bindings.by_sid sid
          { module_name = name; symbol; visibility }
    | _ -> ()
  in
  let visitor =
    object
      inherit [_] G.iter_no_id_info as super

      method! visit_expr env expression =
        (if lang = Some Lang.Scheme then
           match expression.G.e with
           | G.Assign ({ e = G.N (G.Id ((name, _), info)); _ }, _, _)
           | G.AssignOp ({ e = G.N (G.Id ((name, _), info)); _ }, _, _) -> (
               match !(info.G.id_resolved) with
               | Some ((G.ImportedEntity _ | G.ImportedModule _), sid) ->
                   Hashtbl.replace bindings.invalidated_sids sid ()
               | None -> Hashtbl.replace bindings.invalidated_unbound name ()
               | _ -> ())
           | _ -> ());
        super#visit_expr env expression

      method! visit_definition env ((entity, definition) as value) =
        let source expression =
          match expression.G.e with
          | G.Call
              ( { e = G.IdSpecial (G.Require, _); _ },
                (_, [ G.Arg { e = G.L (G.String (_, (name, _), _)); _ } ], _) )
            ->
              Some name
          | _ -> None
        in
        (match (entity.G.name, definition) with
        | G.EN (G.Id (_, info)), G.VarDef { vinit = Some initial_value; _ } -> (
            match source initial_value with
            | Some name -> record info name
            | None -> (
                match initial_value.G.e with
                | G.Assign (left, _, right) ->
                    Option.iter
                      (fun name ->
                        let collect =
                          object
                            inherit [_] G.iter_no_id_info as parent

                            method! visit_expr () expression =
                              (match expression.G.e with
                              | G.N (G.Id (_, info)) -> record info name
                              | _ -> ());
                              parent#visit_expr () expression
                          end
                        in
                        collect#visit_expr () left)
                      (source right)
                | _ -> ()))
        | _ -> ());
        super#visit_definition env value

      method! visit_directive env directive =
        let visibility = Import_visibility.of_attributes directive.G.d_attrs in
        (match directive.G.d with
        | G.ImportAs (_, source, Some ((prefix, _), info)) ->
            let name = module_name source in
            (if lang = Some Lang.Dart || lang = Some Lang.Rust then
               let previous =
                 Option.value ~default:[]
                   (Hashtbl.find_opt bindings.prefixes prefix)
               in
               Hashtbl.replace bindings.prefixes prefix
                 ({ module_name = name; symbol = Some []; visibility }
                 :: previous));
            record ~visibility info name
        | G.ImportFrom (_, source, names) ->
            let name = module_name source in
            if lang = Some Lang.Rust then
              List.iter
                (fun ((original, _), alias) ->
                  let local =
                    match alias with
                    | Some ((local, _), _) -> local
                    | None -> original
                  in
                  let previous =
                    Option.value ~default:[]
                      (Hashtbl.find_opt bindings.prefixes local)
                  in
                  Hashtbl.replace bindings.prefixes local
                    ({
                       module_name = name;
                       symbol = Some [ original ];
                       visibility;
                     }
                    :: previous))
                names;
            List.iter
              (function
                | _, Some (_, info) -> record ~visibility info name
                | (local, _), None ->
                    if Hashtbl.mem bindings.unaliased local then
                      Hashtbl.replace bindings.unaliased local None
                    else
                      Hashtbl.add bindings.unaliased local
                        (Some
                           {
                             module_name = name;
                             symbol = Some [ local ];
                             visibility;
                           }))
              names
        | G.ImportAll (_, source, _)
          when lang = Some Lang.Dart || lang = Some Lang.Scheme
               || lang = Some Lang.Swift ->
            (if lang = Some Lang.Swift then
               match source with
               | G.DottedName [ (name, _) ] ->
                   let previous =
                     Option.value ~default:[]
                       (Hashtbl.find_opt bindings.prefixes name)
                   in
                   Hashtbl.replace bindings.prefixes name
                     ({ module_name = name; symbol = Some []; visibility }
                     :: previous)
               | _ -> ());
            bindings.wildcards <-
              { module_name = module_name source; symbol = Some []; visibility }
              :: bindings.wildcards
        | _ -> ());
        super#visit_directive env directive
    end
  in
  visitor#visit_program () program;
  bindings

let rec origins bindings expression =
  match expression.G.e with
  | G.Call ({ e = G.IdSpecial (G.Require, _); _ },
      (_, [G.Arg { e = G.L (G.String (_, (name, _), _)); _ }], _)) ->
      [{ module_name = name; symbol = Some []; visibility = Import_visibility.unrestricted }]
  | G.N (G.Id (_, info) | G.IdQualified {name_info = info; _})
    when IdFlags.is_native_binding !(info.G.id_flags) -> (
      match !(info.G.id_resolved) with
      | Some (G.ImportedEntity path, _) -> (
          match List.rev path with
          | name :: namespace ->
              [{module_name = String.concat "." (List.rev namespace); symbol = Some [name];
                visibility = Import_visibility.unrestricted}]
          | [] -> [])
      | _ -> [])
  | G.N (G.Id ((name, _), info)) -> (
      match !(info.G.id_resolved) with
      | Some (((G.ImportedModule _ | G.ImportedEntity _) as kind), sid)
        when not (Hashtbl.mem bindings.invalidated_sids sid) -> (
          match Hashtbl.find_opt bindings.prefixes name with
          | Some values -> values
          | None -> (
              match Hashtbl.find_opt bindings.by_sid sid with
              | Some found -> [ found ]
              | None -> (
                  match kind with
                  | G.ImportedEntity _ ->
                      Option.to_list
                        (Option.join (Hashtbl.find_opt bindings.unaliased name))
                  | _ -> [])))
      | _ -> [])
  | G.N
      (G.IdQualified
         { name_middle = None; name_last = name, _; name_top = None; name_info })
    ->
      origins bindings (G.N (G.Id (name, name_info)) |> G.e)
  | G.N
      (G.IdQualified
         {
           name_middle = Some (G.QDots (((prefix, _), _) :: rest));
           name_last = last, _;
           name_top = None;
           name_info;
         }) -> (
      match !(name_info.G.id_resolved) with
      | Some (G.ImportedEntity _, _) ->
          let path =
            List.map (fun ((name, _), _) -> name) rest @ [ fst last ]
          in
          List.map
            (fun origin ->
              {
                origin with
                symbol = Option.map (fun base -> base @ path) origin.symbol;
              })
            (Option.value ~default:[]
               (Hashtbl.find_opt bindings.prefixes prefix))
      | _ -> [])
  | G.DotAccess (receiver, _, field) ->
      let name =
        match field with
        | G.FN (G.Id ((name, _), _)) -> Some name
        | _ -> None
      in
      append_symbol bindings receiver name
  | G.ArrayAccess (receiver, (_, key, _)) ->
      let name =
        match key.G.e with
        | G.L (G.String (_, (name, _), _)) -> Some name
        | _ -> None
      in
      append_symbol bindings receiver name
  | _ -> []

and append_symbol bindings receiver name =
  List.map
    (fun origin ->
      {
        origin with
        symbol =
          Option.bind origin.symbol (fun path ->
              Option.map (fun name -> path @ [ name ]) name);
      })
    (origins bindings receiver)

let visible origin =
  Import_visibility.module_is_fixed origin.visibility origin.module_name
  &&
  match origin.symbol with
  | Some (name :: _) -> Import_visibility.allows origin.visibility name
  | _ -> true

let wildcard_candidates ?imports ~implicit bindings local =
  let implicit_origins =
    if not implicit then []
    else
      Option.fold ~none:[]
        ~some:(fun model ->
          List.map
            (fun module_name ->
              {
                module_name;
                symbol = Some [];
                visibility = Import_visibility.unrestricted;
              })
            model.Rule.implicit_modules)
        imports
  in
  List.filter_map
    (fun origin ->
      Option.bind (Import_visibility.imported_symbol origin.visibility local)
        (fun name ->
          if Import_visibility.allows origin.visibility name then
            Some { origin with symbol = Some [ name ] }
          else None))
    (bindings.wildcards @ implicit_origins)

let wildcard_origins ?imports bindings expression symbol =
  match (expression.G.e, symbol) with
  | G.N (G.Id ((name, _), info)), Some [ _ ]
    when Option.is_none !(info.G.id_resolved)
         && not (Hashtbl.mem bindings.invalidated_unbound name) -> (
      match Hashtbl.find_opt bindings.unaliased name with
      | Some origin -> Option.to_list origin
      | None -> wildcard_candidates ?imports ~implicit:true bindings name)
  | _ -> []

let canonical_origin imports origin =
  let facts =
    Option.fold ~none:[] ~some:(fun model -> model.Rule.export_facts) imports
  in
  let complete =
    Option.fold ~none:[] ~some:(fun model -> model.Rule.complete_exports) imports
  in
  let absent_from_complete module_name name =
    List.exists (fun value ->
        String.equal value.Rule.complete_module module_name
        && not (List.mem name value.Rule.complete_symbols)) complete
  in
  let rec resolve seen origin =
    match origin.symbol with
    | Some (name :: rest) -> (
        let key = (origin.module_name, name) in
        if List.mem key seen then None
        else if absent_from_complete origin.module_name name then Some None
        else
          match
            List.find_opt
              (fun fact ->
                String.equal fact.Rule.export_module origin.module_name
                && String.equal fact.Rule.export_name name)
              facts
          with
          | None -> Some (Some origin)
          | Some { Rule.export_origin = None; _ } -> Some None
          | Some { Rule.export_origin = Some (module_name, symbol); _ } ->
              if
                String.equal module_name origin.module_name && symbol = [ name ]
              then Some (Some origin)
              else
                resolve (key :: seen)
                  { origin with module_name; symbol = Some (symbol @ rest) })
    | _ -> Some (Some origin)
  in
  resolve [] origin

let matches bindings expression ?symbol ?imports modules =
  let resolved =
    match origins bindings expression with
    | [] -> wildcard_origins ?imports bindings expression symbol
    | resolved -> resolved
  in
  let resolved =
    match (expression.G.e, resolved) with
    | G.N (G.Id ((name, _), info)), _ :: _ -> (
        match !(info.G.id_resolved) with
        | Some (G.ImportedEntity _, _) ->
            resolved
            @ wildcard_candidates ?imports ~implicit:false bindings name
        | _ -> resolved)
    | _ -> resolved
  in
  let resolved =
    List.filter
      (fun origin ->
        match origin.symbol with
        | Some (name :: _) -> Import_visibility.allows origin.visibility name
        | _ -> true)
      resolved
  in
  let canonical = List.map (canonical_origin imports) resolved in
  if
    (not (List.for_all visible resolved))
    || List.exists Option.is_none canonical
  then false
  else
    match List.filter_map Option.join canonical with
    | [] -> false
    | first :: rest ->
        List.for_all
          (fun origin ->
            String.equal first.module_name origin.module_name
            && origin.symbol = first.symbol)
          rest
        && List.exists (String.equal first.module_name) modules
        && Option.fold ~none:true
             ~some:(fun expected -> first.symbol = Some expected)
             symbol

let unbound expression =
  match expression.G.e with
  | G.N (G.Id (_, info)) -> Option.is_none !(info.G.id_resolved)
  | G.IdSpecial ((G.Require | G.Eval), _) -> true
  | _ -> false
