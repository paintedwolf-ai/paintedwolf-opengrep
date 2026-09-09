module G = AST_generic

type kind = Module | Function | Class | Comprehension

type binding = { sid : G.sid; mutable identity : G.resolved_name_kind }

type scope = {
  kind : kind;
  parent : scope option;
  bindings : (string, binding) Hashtbl.t;
  redirects : (string, scope) Hashtbl.t;
  mutable opaque : bool;
}

let create kind parent =
  { kind; parent; bindings = Hashtbl.create 16;
    redirects = Hashtbl.create 4; opaque = false }

let local_kind scope = if scope.kind = Module then G.Global else G.LocalVar

let rec assignment_scope scope =
  match scope.kind, scope.parent with
  | Comprehension, Some parent -> assignment_scope parent
  | _ -> scope

let rec module_scope scope =
  match scope.parent with None -> scope | Some parent -> module_scope parent

let rec nonlocal_scope name scope =
  match scope.parent with
  | Some parent when parent.kind = Function && Hashtbl.mem parent.bindings name -> parent
  | Some parent -> nonlocal_scope name parent
  | None -> scope

let destination scope name =
  Option.value ~default:scope (Hashtbl.find_opt scope.redirects name)

let declare scope (name, _) =
  let scope = destination scope name in
  match Hashtbl.find_opt scope.bindings name with
  | Some binding -> binding
  | None ->
      let binding = { sid = G.SId.mk (); identity = local_kind scope } in
      Hashtbl.add scope.bindings name binding;
      binding

let stamp info binding = info.G.id_resolved := Some (binding.identity, binding.sid)

let rec lookup ?(skip_class = false) scope name =
  match Hashtbl.find_opt scope.redirects name with
  | Some target -> lookup target name
  | None ->
      if skip_class && scope.kind = Class then
        Option.bind scope.parent (fun parent -> lookup ~skip_class parent name)
      else
        match Hashtbl.find_opt scope.bindings name with
        | Some binding -> Some binding
        | None when scope.opaque -> Some { sid = G.SId.unsafe_default; identity = G.LocalVar }
        | None -> Option.bind scope.parent (fun parent -> lookup ~skip_class:true parent name)

let pattern_names f = function
  | G.PatId (id, info) -> f id info
  | pattern ->
      let visitor = object
        inherit [_] G.iter_no_id_info as super
        method! visit_pattern () pattern = match pattern with
          | G.PatId (id, info) -> f id info
          | _ -> super#visit_pattern () pattern
      end in
      visitor#visit_pattern () pattern

let rec target_names f expression =
  match expression.G.e with
  | G.N (G.Id (id, info)) -> f id info
  | G.Container (_, (_, values, _)) -> List.iter (target_names f) values
  | G.Cast (_, _, value) -> target_names f value
  | _ -> ()

let import_names f = function
  | G.ImportFrom (_, source, names) ->
      let path = match source with
        | G.DottedName names -> List.map fst names
        | G.FileName (name, _) -> [name] in
      List.iter (fun (id, alias) ->
        let target, info = match alias with
          | Some (id, info) -> (id, Some info)
          | None -> (id, None) in
        f target info (G.ImportedEntity (path @ [fst id]))) names
  | G.ImportAs (_, source, alias) ->
      let path = match source with
        | G.DottedName names -> names
        | G.FileName name -> [name] in
      (match alias, path with
      | Some (id, info), _ -> f id (Some info) (G.ImportedModule (List.map fst path))
      | None, id :: _ -> f id None (G.ImportedModule [fst id])
      | _ -> ())
  | _ -> ()

let collect scope body =
  let outer = ref [] in
  let note id _ = ignore (declare scope id) in
  let visitor = object (self)
    inherit [_] G.iter_no_id_info as super
    method! visit_definition () (entity, definition) =
      (match entity.G.name, definition with
      | G.EN (G.Id ((name, _) as id, _)), G.UseOuterDecl token ->
          outer := (name, Tok.content_of_tok token) :: !outer;
          ignore id
      | G.EN (G.Id (id, info)), _ -> note id info
      | G.EPattern pattern, _ -> pattern_names note pattern
      | _ -> ());
      (match definition with G.FuncDef _ | G.ClassDef _ -> ()
      | _ -> super#visit_definition () (entity, definition))
    method! visit_expr () expression =
      (match expression.G.e with
      | G.Assign (target, _, _) | G.AssignOp (target, _, _) -> target_names note target
      | G.LetPattern (pattern, _) -> pattern_names note pattern
      | _ -> ());
      match expression.G.e with
      | G.Lambda _ | G.AnonClass _ -> ()
      | G.Comprehension (_, (_, (value, clauses), _)) ->
          self#visit_expr () value;
          List.iter (function
            | G.CompFor (_, _, _, iterable) | G.CompIf (_, iterable) ->
                self#visit_expr () iterable) clauses
      | _ -> super#visit_expr () expression
    method! visit_pattern () pattern = pattern_names note pattern
    method! visit_directive () directive =
      import_names (fun id _ _ -> ignore (declare scope id)) directive.G.d
    method! visit_parameter () parameter =
      match parameter with
      | G.Param { pname = Some id; pinfo; _ }
      | G.ParamRest (_, { pname = Some id; pinfo; _ })
      | G.ParamHashSplat (_, { pname = Some id; pinfo; _ }) -> note id pinfo
      | _ -> super#visit_parameter () parameter
    method! visit_catch () ((_, pattern, _) as catch) =
      (match pattern with
      | G.CatchParam { pname = Some id; pinfo; _ } -> note id pinfo
      | _ -> ());
      super#visit_catch () catch
    method! visit_stmt () statement =
      (match statement.G.s with
      | G.OtherStmt (G.OS_Delete, values) ->
          List.iter (function G.E value -> target_names note value | _ -> ()) values
      | _ -> ());
      super#visit_stmt () statement
  end in
  visitor#visit_function_body () body;
  List.iter (fun (name, directive) ->
    Hashtbl.remove scope.bindings name;
    let target = if directive = "global" then module_scope scope else nonlocal_scope name scope in
    if target != scope then Hashtbl.replace scope.redirects name target) !outer

let resolve program =
  let deferred = ref [] in
  let imported_names = Hashtbl.create 16 in
  let read scope id info =
    let name = fst id in
    let apply () =
      match lookup scope name with
      | Some binding -> stamp info binding
      | None -> info.G.id_resolved := None in
    let own = Hashtbl.mem scope.bindings name && not (Hashtbl.mem scope.redirects name) in
    if scope.kind = Function && not own then deferred := apply :: !deferred
    else apply ()
  in
  let write scope id info =
    let binding = declare scope id in
    binding.identity <- local_kind (destination scope (fst id));
    stamp info binding
  in
  let visitor = object (self)
    inherit [_] G.iter_no_id_info as super
    method! visit_name scope = function
      | G.Id (id, info) -> read scope id info
      | name -> super#visit_name scope name
    method! visit_field_name scope = function
      | G.FDynamic value -> self#visit_expr scope value
      | G.FN _ -> ()
    method! visit_definition scope (entity, definition) =
      List.iter (self#visit_attribute scope) entity.G.attrs;
      match definition with
      | G.UseOuterDecl token ->
          (match entity.G.name with
          | G.EN (G.Id ((name, _), _)) ->
              let target = if Tok.content_of_tok token = "global" then module_scope scope
                else nonlocal_scope name scope in
              if target != scope then Hashtbl.replace scope.redirects name target
          | _ -> ())
      | G.FuncDef function_ ->
          self#visit_function_definition scope function_;
          (match entity.G.name with G.EN (G.Id (id, info)) -> write scope id info | _ -> ())
      | G.ClassDef class_ ->
          self#visit_class_definition scope class_;
          (match entity.G.name with G.EN (G.Id (id, info)) -> write scope id info | _ -> ())
      | G.VarDef variable ->
          Option.iter (self#visit_expr scope) variable.G.vinit;
          Option.iter (self#visit_type_ scope) variable.G.vtype;
          (match entity.G.name with
          | G.EN (G.Id (id, info)) -> write scope id info
          | G.EPattern pattern -> pattern_names (write scope) pattern
          | _ -> ())
      | _ -> super#visit_definition scope (entity, definition)
    method! visit_function_definition scope function_ =
      let parameters = Tok.unbracket function_.G.fparams in
      List.iter (self#visit_parameter scope) parameters;
      Option.iter (self#visit_type_ scope) function_.G.frettype;
      let local = create Function (Some scope) in
      collect local function_.G.fbody;
      List.iter (function
        | G.Param { pname = Some id; pinfo; _ }
        | G.ParamRest (_, { pname = Some id; pinfo; _ })
        | G.ParamHashSplat (_, { pname = Some id; pinfo; _ }) ->
            let binding = declare local id in binding.identity <- G.Parameter; stamp pinfo binding
        | G.ParamPattern (pattern, _) -> pattern_names (write local) pattern
        | _ -> ()) parameters;
      self#visit_function_body local function_.G.fbody
    method! visit_parameter scope parameter =
      match parameter with
      | G.Param classic | G.ParamRest (_, classic) | G.ParamHashSplat (_, classic) ->
          Option.iter (self#visit_expr scope) classic.G.pdefault;
          Option.iter (self#visit_type_ scope) classic.G.ptype;
          List.iter (self#visit_attribute scope) classic.G.pattrs
      | _ -> super#visit_parameter scope parameter
    method! visit_class_definition scope class_ =
      let _, fields, _ = class_.G.cbody in
      let empty = { class_ with G.cbody = Tok.unsafe_fake_bracket [] } in
      super#visit_class_definition scope empty;
      let local = create Class (Some scope) in
      List.iter (self#visit_field local) fields
    method! visit_directive scope directive =
      (match directive.G.d with G.ImportAll _ -> scope.opaque <- true | _ -> ());
      import_names (fun id info identity ->
        let binding = { sid = G.SId.mk (); identity } in
        Hashtbl.replace (destination scope (fst id)).bindings (fst id) binding;
        let info = Option.value ~default:(G.empty_id_info ()) info in
        stamp info binding;
        Hashtbl.replace imported_names id info) directive.G.d
    method! visit_pattern scope pattern = pattern_names (write scope) pattern
    method! visit_for_header scope = function
      | G.ForEach (pattern, _, iterable) ->
          self#visit_expr scope iterable; pattern_names (write scope) pattern
      | header -> super#visit_for_header scope header
    method! visit_catch scope (token, pattern, body) =
      (match pattern with
      | G.CatchParam classic ->
          Option.iter (self#visit_type_ scope) classic.G.ptype;
          Option.iter (fun id -> write scope id classic.G.pinfo) classic.G.pname
      | G.CatchPattern pattern -> self#visit_pattern scope pattern
      | _ -> super#visit_catch_exn scope pattern);
      ignore token;
      self#visit_stmt scope body
    method! visit_stmt scope statement =
      (match statement.G.s with
      | G.OtherStmt (G.OS_Delete, values) ->
          List.iter (function G.E value -> target_names (write scope) value | _ -> ()) values
      | _ -> ());
      super#visit_stmt scope statement;
      (match statement.G.s with
      | G.If _ | G.For _ | G.While _ | G.Try _ ->
          let branch = create Function (Some scope) in
          collect branch (G.FBStmt statement);
          Hashtbl.iter (fun name _ ->
            let destination = destination scope name in
            Option.iter (fun binding -> binding.identity <- local_kind destination)
              (Hashtbl.find_opt destination.bindings name)) branch.bindings
      | _ -> ())
    method! visit_expr scope expression =
      match expression.G.e with
      | G.Assign (target, _, value) | G.AssignOp (target, _, value) ->
          self#visit_expr scope value;
          self#visit_expr scope target;
          target_names (write (assignment_scope scope)) target
      | G.LetPattern (pattern, value) ->
          self#visit_expr scope value; pattern_names (write scope) pattern
      | G.Comprehension (_, (_, (value, clauses), _)) ->
          let local = create Comprehension (Some scope) in
          List.iteri (fun index -> function
            | G.CompFor (_, pattern, _, iterable) ->
                self#visit_expr (if index = 0 then scope else local) iterable;
                pattern_names (write local) pattern
            | G.CompIf (_, condition) -> self#visit_expr local condition) clauses;
          self#visit_expr local value
      | _ -> super#visit_expr scope expression
  end in
  visitor#visit_program (create Module None) program;
  List.iter (fun apply -> apply ()) !deferred;
  let mapper = object
    inherit [_] G.map as super
    method! visit_directive () directive =
      let directive = super#visit_directive () directive in
      match directive.G.d with
      | G.ImportFrom (token, source, names) ->
          let names = List.map (function
            | id, None -> (id, Option.map (fun info -> (id, info))
                                   (Hashtbl.find_opt imported_names id))
            | imported -> imported) names in
          { directive with G.d = G.ImportFrom (token, source, names) }
      | G.ImportAs (token, G.DottedName (id :: _ as path), None) ->
          let alias = Option.map (fun info -> (id, info)) (Hashtbl.find_opt imported_names id) in
          { directive with G.d = G.ImportAs (token, G.DottedName path, alias) }
      | _ -> directive
  end in
  mapper#visit_program () program
