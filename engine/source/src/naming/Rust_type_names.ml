module G = AST_generic

type scope = {
  names : (string, binding) Hashtbl.t;
  mutable opaque : bool;
  mutable standard_prelude : bool;
}

and binding =
  | Local
  | Import of int * string list * scope list
  | Alias of int * G.type_ * scope list

type state = {
  primitives : (string, G.sid) Hashtbl.t;
  externs : (string, string option) Hashtbl.t;
  mutable next_alias : int;
}

let primitive = function
  | "u8" | "u16" | "u32" | "u64" | "u128" | "usize"
  | "i8" | "i16" | "i32" | "i64" | "i128" | "isize"
  | "f32" | "f64" | "bool" | "char" | "str" -> true
  | _ -> false

let scope () = { names = Hashtbl.create 16; opaque = false; standard_prelude = true }

let rec lookup name = function
  | [] -> None
  | frame :: outer -> (
      match Hashtbl.find_opt frame.names name with
      | Some found -> Some found
      | None when frame.opaque -> Some Local
      | None -> lookup name outer)

let identifier = function
  | G.EN (G.Id ((name, _), _)) -> Some name
  | _ -> None

let qualified = function
  | G.Id ((name, _), _) -> Some (false, [name])
  | G.IdQualified { name_middle; name_last = (name, _), arguments; name_top; _ }
    when Option.is_none arguments -> (
      match name_middle with
      | None -> Some (Option.is_some name_top, [name])
      | Some (G.QDots path)
        when List.for_all (fun (_, args) -> Option.is_none args) path ->
          Some (Option.is_some name_top,
            List.map (fun ((part, _), _) -> part) path @ [name])
      | _ -> None)
  | _ -> None

let external_root state name =
  match Hashtbl.find_opt state.externs name with
  | Some found -> found
  | None when name = "core" || name = "std" || name = "alloc" -> Some name
  | None -> None

let rec type_ state seen scopes value =
  match value.G.t with
  | G.TyN name -> Option.bind (qualified name) (fun (absolute, path) ->
      resolve state seen scopes ~absolute path)
  | _ -> None

and resolve state seen scopes ~absolute path =
  match path with
  | [name] when not absolute -> (
      match lookup name scopes with
      | Some (Alias (id, value, declaration_scopes))
        when not (List.mem id seen) ->
          type_ state (id :: seen) declaration_scopes value
      | Some (Import (id, imported, declaration_scopes))
        when not (List.mem id seen) ->
          resolve_import state (id :: seen) declaration_scopes imported []
      | Some _ -> None
      | None when not (List.exists (fun frame -> frame.opaque) scopes)
                  && (primitive name || (name = "String"
                      && List.for_all (fun frame -> frame.standard_prelude) scopes)) ->
          Some name
      | None -> None)
  | root :: tail ->
      if absolute then resolve_external state root tail
      else resolve_import state seen scopes [root] tail
  | [] -> None

and resolve_import state seen scopes imported tail =
  match imported with
  | [] -> None
  | root :: rest -> (
      match lookup root scopes with
      | Some (Import (id, replacement, declaration_scopes))
        when not (List.mem id seen) ->
          resolve_import state (id :: seen) declaration_scopes replacement (rest @ tail)
      | Some (Import (id, [same], declaration_scopes))
        when List.mem id seen && same = root && imported = [root] ->
          let outer = match declaration_scopes with _ :: outer -> outer | [] -> [] in
          resolve_import state seen outer imported tail
      | Some _ -> None
      | None when not (List.exists (fun frame -> frame.opaque) scopes) ->
          resolve_external state root (rest @ tail)
      | None -> None)

and resolve_external state root tail =
  match (external_root state root, tail) with
  | Some ("core" | "std"), ["primitive"; name] when primitive name -> Some name
  | Some ("std" | "alloc"), ["string"; "String"] -> Some "String"
  | _ -> None

let rec native_namespace state seen scopes ~explicit path =
  match path with
  | [] | ("crate" | "self" | "super") :: _ -> None
  | root :: tail -> (
      if explicit then
        (match root with
        | "std" | "core" | "alloc" ->
            Option.map (fun root -> root :: tail) (external_root state root)
        | _ -> None)
      else match lookup root scopes with
      | Some (Import (id, imported, declaration_scopes))
        when not (List.mem id seen) ->
          imported_namespace state (id :: seen) declaration_scopes (imported @ tail)
      | Some (Alias (id, {G.t = G.TyN name; _}, declaration_scopes))
        when not (List.mem id seen) ->
          Option.bind (qualified name) (fun (absolute, path) ->
            native_namespace state (id :: seen) declaration_scopes ~explicit:absolute (path @ tail))
      | Some _ -> None
      | None when not (List.exists (fun frame -> frame.opaque) scopes)
               && (root = "std" || root = "core" || root = "alloc")
               && List.for_all (fun frame -> frame.standard_prelude) scopes ->
          Option.map (fun root -> root :: tail) (external_root state root)
      | None -> None)

and imported_namespace state seen scopes path =
  match path with
  | [] | ("crate" | "self" | "super") :: _ -> None
  | root :: tail -> (
      match lookup root scopes with
      | Some (Import (id, imported, declaration_scopes))
        when not (List.mem id seen) ->
          imported_namespace state (id :: seen) declaration_scopes (imported @ tail)
      | Some (Import (id, [same], declaration_scopes))
        when List.mem id seen && same = root ->
          let outer = match declaration_scopes with _ :: outer -> outer | [] -> [] in
          imported_namespace state seen outer path
      | Some _ -> None
      | None when not (List.exists (fun frame -> frame.opaque) scopes) ->
          native_namespace state seen scopes ~explicit:true path
      | None -> None)

let expression_path = function
  | G.IdQualified {name_middle; name_last = (name, _), _; name_top; _} -> (
      match name_middle with
      | Some (G.QDots path) ->
          Some (Option.is_some name_top,
            List.map (fun ((part, _), _) -> part) path @ [name])
      | _ -> None)
  | _ -> None

let add frame name binding =
  match Hashtbl.find_opt frame.names name with
  | None -> Hashtbl.add frame.names name binding
  | Some _ -> Hashtbl.replace frame.names name Local

let macro_expression expression =
  match expression.G.e with
  | G.Call ({ e = G.N name; _ }, _) -> (
      let name = match name with
        | G.Id ((name, _), _) -> name
        | G.IdQualified {name_last = (name, _), _; _} -> name
      in
      String.ends_with ~suffix:"!" name)
  | _ -> false

let disables_standard_prelude = function
  | G.NamedAttr (_, G.Id ((("no_std" | "no_core" | "no_implicit_prelude" | "cfg_attr"), _), _), _) -> true
  | _ -> false

(* Type declarations are visible throughout their enclosing scope. *)
let declarations state scopes frame statements =
  List.iter (fun statement -> match statement.G.s with
    | G.DefStmt (entity, definition) -> (
        match (identifier entity.G.name, definition) with
        | Some name, G.TypeDef {tbody = G.AliasType value} ->
            state.next_alias <- state.next_alias + 1;
            add frame name (Alias (state.next_alias, value, scopes))
        | Some name, (G.TypeDef _ | G.ClassDef _ | G.ModuleDef _) -> add frame name Local
        | _ -> ())
    | G.DirectiveStmt { d = G.ImportFrom (_, G.DottedName path, names); _ } ->
        List.iter (fun ((original, _), alias) ->
          let local = match alias with Some ((name, _), _) -> name | None -> original in
          state.next_alias <- state.next_alias + 1;
          add frame local (Import (state.next_alias, List.map fst path @ [original], scopes))) names
    | G.DirectiveStmt { d = G.ImportAs (token, G.DottedName [(name, _)], None); _ }
      when Tok.content_of_tok token = "extern" ->
        state.next_alias <- state.next_alias + 1;
        add frame name (Import (state.next_alias, [name], scopes))
    | G.DirectiveStmt { d = G.ImportAs (_, G.DottedName path, Some ((name, _), _)); _ } ->
        state.next_alias <- state.next_alias + 1;
        add frame name (Import (state.next_alias, List.map fst path, scopes))
    | G.DirectiveStmt {d = G.OtherDirective (("rust_inner_attribute", _), [G.At attribute]); _}
      when disables_standard_prelude attribute -> frame.standard_prelude <- false
    | G.DirectiveStmt { d = G.ImportAll _; _ } -> frame.opaque <- true
    | G.ExprStmt (expression, _) when macro_expression expression -> frame.opaque <- true
    | _ -> ()) statements

let clear info =
  info.G.id_flags := IdFlags.clear_native_binding !(info.G.id_flags)

let rec external_import seen scopes path =
  match path with
  | [] | ("crate" | "self" | "super") :: _ -> false
  | root :: tail -> (
      match lookup root scopes with
      | Some (Import (id, imported, declaration_scopes))
        when not (List.mem id seen) ->
          external_import (id :: seen) declaration_scopes (imported @ tail)
      | Some (Import (id, [same], declaration_scopes))
        when List.mem id seen && same = root ->
          let outer = match declaration_scopes with _ :: outer -> outer | [] -> [] in
          external_import seen outer path
      | Some _ -> false
      | None -> not (List.exists (fun frame -> frame.opaque) scopes))

let disqualify_import info =
  match !(info.G.id_resolved) with
  | Some ((G.ImportedEntity _ | G.ImportedModule _), sid) ->
      info.G.id_resolved := Some (G.TypeName, sid);
      info.G.id_resolved_alternatives := []
  | _ -> ()

let type_name_binding scopes name =
  let root, info, absolute = match name with
    | G.Id ((name, _), info) -> Some name, info, false
    | G.IdQualified {name_middle; name_last = (name, _), _; name_info; name_top} ->
        let root = match name_middle with
          | None -> Some name
          | Some (G.QDots (((root, _), _) :: _)) -> Some root
          | _ -> None
        in
        root, name_info, Option.is_some name_top
  in
  if not absolute && not (IdFlags.is_native_binding !(info.G.id_flags)) then
    Option.iter (fun root ->
      match lookup root scopes with
      | Some (Import (id, imported, declaration_scopes)) ->
          if not (external_import [id] declaration_scopes imported) then
            disqualify_import info
          else (match !(info.G.id_resolved) with
          | Some (G.ImportedEntity [("core" | "std"); "primitive"; name], _)
            when primitive name ->
              disqualify_import info
          | _ -> ())
      | Some Local | Some (Alias _) | None ->
          disqualify_import info) root

let mark_native state info origin =
  let key = String.concat "." origin in
  let sid = match Hashtbl.find_opt state.primitives key with
    | Some sid -> sid
    | None -> let sid = G.SId.mk () in Hashtbl.add state.primitives key sid; sid
  in
  info.G.id_resolved := Some (G.ImportedEntity origin, sid);
  info.G.id_flags := IdFlags.set_native_binding !(info.G.id_flags)

let mark state info name =
  let origin = if name = "String" then ["std"; "string"; "String"]
    else ["core"; "primitive"; name] in
  mark_native state info origin

let resolve_program program =
  let state = {primitives = Hashtbl.create 16; externs = Hashtbl.create 4; next_alias = 0} in
  let external_declarations = object
    inherit [_] G.iter_no_id_info as super
    method! visit_directive () directive =
      (match directive.G.d with
      | G.ImportAs (token, G.DottedName path, alias)
        when Tok.content_of_tok token = "extern" ->
          let imported = List.map fst path in
          let name = match alias, List.rev imported with
            | Some ((name, _), _), _ -> Some name
            | None, name :: _ -> Some name
            | _ -> None
          in
          Option.iter (fun name ->
            let root = match imported with [(("core" | "std" | "alloc") as root)] -> Some root | _ -> None in
            match Hashtbl.find_opt state.externs name with
            | None -> Hashtbl.add state.externs name root
            | Some previous when previous = root -> ()
            | Some _ -> Hashtbl.replace state.externs name None) name
      | _ -> ());
      super#visit_directive () directive
  end in
  external_declarations#visit_program () program;
  let visitor = object(self)
    inherit [_] G.iter_no_id_info as super

    method private statements ?(standard_prelude = true) outer statements =
      let frame = scope () in
      frame.standard_prelude <- standard_prelude;
      let scopes = frame :: outer in
      declarations state scopes frame statements;
      List.iter (self#visit_stmt scopes) statements

    method! visit_program _ program = self#statements [] program

    method! visit_type_ scopes value =
      (match value.G.t with
      | G.TyN name ->
          let info = match name with G.Id (_, info) -> info | G.IdQualified {name_info; _} -> name_info in
          clear info;
          (match type_ state [] scopes value with
          | Some name -> mark state info name
          | None -> type_name_binding scopes name)
      | _ -> ());
      super#visit_type_ scopes value

    method! visit_expr scopes expression =
      (match expression.G.e with
      | G.N ((G.IdQualified _ | G.Id _) as name) ->
          let origin = Option.bind (expression_path name) (fun (absolute, path) ->
            native_namespace state [] scopes ~explicit:absolute path) in
          (match origin, name with
          | Some origin, G.IdQualified {name_info; name_top; _}
            when Option.is_some name_top || (match !(name_info.G.id_resolved) with
                 | Some ((G.ImportedEntity _ | G.ImportedModule _), _) -> false
                 | _ -> true) -> mark_native state name_info origin
          | _ -> type_name_binding scopes name)
      | _ -> ());
      super#visit_expr scopes expression

    method! visit_pattern scopes pattern =
      (match pattern with
      | G.PatConstructor (name, _) -> type_name_binding scopes name
      | _ -> ());
      super#visit_pattern scopes pattern

    method! visit_stmt scopes statement =
      match statement.G.s with
      | G.Block (_, statements, _) -> self#statements scopes statements
      | _ -> super#visit_stmt scopes statement

    method! visit_definition scopes ((entity, definition) as value) =
      let scopes = match entity.G.tparams with
        | None -> scopes
        | Some (_, parameters, _) ->
            let frame = scope () in
            List.iter (function G.TP {tp_id = (name, _); _} -> add frame name Local | _ -> ()) parameters;
            frame :: scopes
      in
      match definition with
      | G.ModuleDef {mbody = G.ModuleStruct (_, statements)} ->
          let standard_prelude =
            List.for_all (fun frame -> frame.standard_prelude) scopes
            && not (List.exists disables_standard_prelude entity.G.attrs)
          in
          self#statements ~standard_prelude [] statements
      | _ -> super#visit_definition scopes value
  end in
  visitor#visit_program [] program;
  program
