module G = AST_generic

type scope = {
  parent : scope option;
  function_scope : bool;
  strict : bool;
  bindings : (string, G.id_info) Hashtbl.t;
  type_bindings : (string, G.id_info) Hashtbl.t;
}

type use = { name : string; info : G.id_info; scope : scope }

let child ~function_scope parent =
  { parent; function_scope;
    strict = Option.fold ~none:false ~some:(fun scope -> scope.strict) parent;
    bindings = Hashtbl.create 16; type_bindings = Hashtbl.create 8 }

let rec function_scope scope =
  if scope.function_scope then scope
  else
    match scope.parent with
    | Some parent -> function_scope parent
    | None -> scope

let rec lookup scope name =
  match Hashtbl.find_opt scope.bindings name with
  | Some _ as result -> result
  | None -> Option.bind scope.parent (fun parent -> lookup parent name)

let declare scope (name, _) info =
  if Option.is_none !(info.G.id_resolved) then
    info.G.id_resolved :=
      Some
        ( (if Option.is_none scope.parent then G.Global else G.LocalVar),
          G.SId.mk () );
  match Hashtbl.find_opt scope.bindings name with
  | None -> Hashtbl.add scope.bindings name info
  | Some previous -> info.G.id_resolved := !(previous.G.id_resolved)

let rec lookup_type scope name =
  match Hashtbl.find_opt scope.type_bindings name with
  | Some _ as result -> result
  | None -> (
      match Hashtbl.find_opt scope.bindings name with
      | Some info when (match !(info.G.id_resolved) with
          | Some ((G.ImportedModule _ | G.ImportedEntity _), _) -> true
          | _ -> false) -> Some info
      | _ -> Option.bind scope.parent (fun parent -> lookup_type parent name))

let declare_type scope (name, _) info =
  info.G.id_resolved := Some (G.LocalVar, G.SId.mk ());
  Hashtbl.replace scope.type_bindings name info

let strict_body statements =
  let rec directives = function
    | { G.s = G.ExprStmt ({ e = G.OtherExpr (("UseStrict", _), []); _ }, _); _ } :: _ -> true
    | { G.s = G.ExprStmt ({ e = G.L (G.String (_, ("use strict", _), _)); _ }, _); _ } :: _ -> true
    | { G.s = G.ExprStmt ({ e = G.L (G.String _); _ }, _); _ } :: rest -> directives rest
    | _ -> false
  in
  directives statements

let body_statements = function
  | G.FBStmt { s = G.Block (_, statements, _); _ } -> statements
  | _ -> []

let resolve program =
  let uses = ref [] in
  let type_uses = ref [] in
  let implicit_arguments = ref [] in
  let special_uses = ref [] in
  let requires = ref [] in
  let import_bindings = Hashtbl.create 16 in
  let imported_info info =
    match !(info.G.id_resolved) with
    | Some ((G.ImportedEntity _ | G.ImportedModule _), _) -> true
    | _ -> false
  in
  let require_call expression =
    match expression.G.e with
    | G.Call ({ e = G.IdSpecial (G.Require, _); _ }, _) -> true
    | _ -> false
  in
  let visitor =
    object (self)
      inherit [_] G.iter_no_id_info as super

      method private declare_pattern scope =
        function
        | G.PatId (id, info) -> declare scope id info
        | G.PatAs (pattern, (id, info)) ->
            self#declare_pattern scope pattern;
            declare scope id info
        | G.PatTyped (pattern, _) -> self#declare_pattern scope pattern
        | G.PatTuple (_, patterns, _)
        | G.PatList (_, patterns, _)
        | G.PatConstructor (_, patterns) ->
            List.iter (self#declare_pattern scope) patterns
        | G.PatRecord (_, fields, _) ->
            List.iter
              (fun (_, pattern) -> self#declare_pattern scope pattern)
              fields
        | G.OtherPat (_, values) ->
            List.iter
              (function
                | G.E expression -> self#declare_expression scope expression
                | G.P pattern -> self#declare_pattern scope pattern
                | _ -> ())
              values
        | _ -> ()

      method private declare_expression scope expression =
        match expression.G.e with
        | G.N (G.Id (id, info)) -> declare scope id info
        | G.Assign (left, _, _) -> self#declare_expression scope left
        | G.Container (_, (_, elements, _)) ->
            List.iter (self#declare_expression scope) elements
        | G.Record (_, fields, _) ->
            List.iter
              (function
                | G.F
                    {
                      s =
                        G.DefStmt (_, G.FieldDefColon { vinit = Some value; _ });
                      _;
                    } ->
                    self#declare_expression scope value
                | G.F { s = G.ExprStmt (value, _); _ } ->
                    self#declare_expression scope value
                | _ -> ())
              fields
        | G.Call ({ e = G.IdSpecial (G.Spread, _); _ }, (_, [ G.Arg value ], _))
          ->
            self#declare_expression scope value
        | _ -> ()

      method! visit_definition scope ((entity, definition) as value) =
        let destination =
          match definition with
          | G.VarDef _
            when List.exists
                   (function
                     | G.KeywordAttr (G.Var, _) -> true
                     | _ -> false)
                   entity.G.attrs ->
              function_scope scope
          | _ -> scope
        in
        (match (entity.G.name, definition) with
        | ( G.EN (G.Id ((name, _), _)),
            G.VarDef { vinit = Some { e = G.Assign (left, _, _); _ }; _ } )
          when String.equal name G.special_multivardef_pattern ->
            self#declare_expression destination left
        | G.EN (G.Id (id, info)), (G.VarDef _ | G.FuncDef _ | G.ClassDef _) ->
            declare destination id info
        | G.EPattern pattern, G.VarDef _ ->
            self#declare_pattern destination pattern
        | _ -> ());
        (match (entity.G.name, definition) with
        | ( G.EN (G.Id ((name, _), info)),
            G.VarDef { vinit = Some initial_value; _ } ) -> (
            if require_call initial_value && imported_info info then
              requires := (scope, info) :: !requires
            else if String.equal name G.special_multivardef_pattern then
              match initial_value.G.e with
              | G.Assign (left, _, right) when require_call right ->
                  let collect =
                    object
                      inherit [_] G.iter_no_id_info as parent

                      method! visit_expr () expression =
                        (match expression.G.e with
                        | G.N (G.Id ((name, _), info)) when imported_info info
                          -> (
                            match lookup destination name with
                            | Some declaration when declaration == info ->
                                requires := (scope, info) :: !requires
                            | _ -> ())
                        | _ -> ());
                        parent#visit_expr () expression
                    end
                  in
                  collect#visit_expr () left
              | _ -> ())
        | _ -> ());
        (match (entity.G.name, definition) with
        | G.EN (G.Id (id, _)), (G.TypeDef _ | G.ClassDef _ | G.OtherDef (("typedef", _), _)) ->
            let type_info = G.empty_id_info () in
            declare_type scope id type_info
        | _ -> ());
        let scope = match entity.G.tparams with
          | None -> scope
          | Some (_, parameters, _) ->
              let local = child ~function_scope:false (Some scope) in
              List.iter (function
                | G.TP parameter -> declare_type local parameter.G.tp_id (G.empty_id_info ())
                | _ -> ()) parameters;
              local
        in
        super#visit_definition scope value

      method! visit_field scope =
        function
        | G.F { s = G.DefStmt (entity, definition); _ } ->
            let parameters = List.concat_map (function
              | G.OtherAttribute (("TypeParameters", _), parameters) -> parameters
              | _ -> []) entity.G.attrs in
            let scope = if List.is_empty parameters then scope else
              let local = child ~function_scope:false (Some scope) in
              List.iter (function G.I id -> declare_type local id (G.empty_id_info ())
                | _ -> ()) parameters; local in
            List.iter (self#visit_attribute scope) entity.G.attrs;
            super#visit_definition_kind scope definition
        | field -> super#visit_field scope field

      method! visit_parameter scope value =
        (match value with
        | G.Param { pname = Some id; pinfo; _ }
        | G.ParamRest (_, { pname = Some id; pinfo; _ }) ->
            declare scope id pinfo
        | G.ParamPattern (pattern, _) -> self#declare_pattern scope pattern
        | _ -> ());
        super#visit_parameter scope value

      method! visit_function_definition scope definition =
        let scope = child ~function_scope:true (Some scope) in
        let scope = { scope with strict = scope.strict || strict_body (body_statements definition.G.fbody) } in
        let parameters = Tok.unbracket definition.G.fparams in
        List.iter (self#visit_parameter scope) parameters;
        (match fst definition.G.fkind with
        | G.Arrow -> ()
        | _ when Hashtbl.mem scope.bindings "arguments" -> ()
        | _ ->
            let token = snd definition.G.fkind in
            let info = G.empty_id_info () in
            declare scope ("arguments", token) info;
            let mapped = not scope.strict && not (List.is_empty parameters)
                && List.for_all (function G.Param { pdefault = None; _ } -> true | _ -> false) parameters in
            implicit_arguments := (definition, info, mapped) :: !implicit_arguments);
        Option.iter (self#visit_type_ scope) definition.G.frettype;
        self#visit_function_body scope definition.G.fbody

      method! visit_function_body parameters body =
        let scope = child ~function_scope:true (Some parameters) in
        Hashtbl.iter (Hashtbl.add scope.bindings) parameters.bindings;
        super#visit_function_body scope body

      method! visit_class_definition scope definition =
        let scope = child ~function_scope:false (Some scope) in
        super#visit_class_definition { scope with strict = true } definition

      method! visit_catch scope catch =
        let scope = child ~function_scope:false (Some scope) in
        let _, pattern, _ = catch in
        (match pattern with
        | G.CatchPattern pattern -> self#declare_pattern scope pattern
        | G.CatchParam { pname = Some id; pinfo; _ } -> declare scope id pinfo
        | _ -> ());
        super#visit_catch scope catch

      method! visit_stmt scope statement =
        match statement.G.s with
        | G.Block _
        | G.Switch _
        | G.For _ ->
            super#visit_stmt
              (child ~function_scope:false (Some scope))
              statement
        | _ -> super#visit_stmt scope statement

      method! visit_for_header scope header =
        (match header with
        | G.ForClassic (initial_values, _, _) ->
            List.iter
              (function
                | G.ForInitVar (entity, variable) ->
                    self#visit_definition scope (entity, G.VarDef variable)
                | _ -> ())
              initial_values
        | G.ForEach (pattern, _, _) -> self#declare_pattern scope pattern
        | _ -> ());
        super#visit_for_header scope header

      method! visit_directive scope directive =
        (match directive.G.d with
        | G.ImportAs (_, _, Some (id, info)) -> declare scope id info
        | G.ImportFrom (_, source, imports) ->
            List.iter
              (function
                | _, Some (id, info) -> declare scope id info
                | id, None ->
                    let canonical =
                      match source with
                      | G.FileName (name, _) ->
                          let _, base, _ =
                            Filename_.dbe_of_filename_noext_ok name
                          in
                          [ base; fst id ]
                      | G.DottedName names ->
                          G.dotted_to_canonical (names @ [ id ])
                    in
                    let info = G.empty_id_info () in
                    info.G.id_resolved :=
                      Some (G.ImportedEntity canonical, G.SId.mk ());
                    declare scope id info;
                    Hashtbl.replace import_bindings id info)
              imports
        | _ -> ());
        super#visit_directive scope directive

      method! visit_type_ scope type_ =
        (match type_.G.t with
        | G.TyN (G.Id ((name, _), info)) -> type_uses := { name; info; scope } :: !type_uses
        | _ -> ());
        super#visit_type_ scope type_

      method! visit_expr scope expression =
        let scope =
          match expression.G.e with
          | G.OtherExpr (("TypeParameters", _), G.E _ :: parameters) ->
              let local = child ~function_scope:false (Some scope) in
              List.iter (function G.I id -> declare_type local id (G.empty_id_info ())
                | _ -> ()) parameters;
              local
          | G.OtherExpr
              (("NamedExpression", _), [ G.Name (G.Id (id, info)); G.E _ ]) ->
              let scope = child ~function_scope:false (Some scope) in
              declare scope id info;
              scope
          | _ -> scope
        in
        (match expression.G.e with
        | G.N (G.Id ((name, _), info)) -> uses := { name; info; scope } :: !uses
        | G.IdSpecial ((G.Require | G.Eval), tok)
        | G.L (G.Undefined tok)
        | G.OtherExpr ((("Define" | "Arguments"), tok), []) ->
            special_uses :=
              (expression, Tok.content_of_tok tok, tok, scope) :: !special_uses
        | G.LetPattern (pattern, _) -> self#declare_pattern scope pattern
        | _ -> ());
        super#visit_expr scope expression
    end
  in
  let module_code = List.exists (function
      | { G.s = G.DirectiveStmt { d = G.ImportFrom _ | G.ImportAs _ | G.ImportAll _; _ }; _ }
      | { G.s = G.DirectiveStmt { d = G.OtherDirective ((("Export" | "ReExportNamespace"), _), _); _ }; _ } -> true
      | _ -> false) program in
  let scope = child ~function_scope:true None in
  visitor#visit_program { scope with strict = module_code || strict_body program } program;
  List.iter
    (fun (scope, info) ->
      if Option.is_some (lookup scope "require") then
        match !(info.G.id_resolved) with
        | Some (_, sid) -> info.G.id_resolved := Some (G.LocalVar, sid)
        | None -> ())
    !requires;
  List.iter
    (fun { name; info; scope } ->
      match lookup scope name with
      | Some declaration -> info.G.id_resolved := !(declaration.G.id_resolved)
      | None -> info.G.id_resolved := None)
    !uses;
  List.iter
    (fun { name; info; scope } ->
      info.G.id_resolved := Option.bind (lookup_type scope name)
        (fun declaration -> !(declaration.G.id_resolved)))
    !type_uses;
  let module Expressions = Hashtbl.Make (struct
    type t = G.expr

    let equal left right = left == right
    let hash expression = Hashtbl.hash expression
  end) in
  let replacements = Expressions.create (List.length !special_uses) in
  List.iter
    (fun (expression, name, tok, scope) ->
      match lookup scope name with
      | None -> ()
      | Some declaration ->
          let info = G.empty_id_info () in
          info.G.id_resolved := !(declaration.G.id_resolved);
          let kind =
            match List.find_opt (fun (_, implicit, _) -> implicit == declaration) !implicit_arguments with
            | Some (_, _, true) -> G.OtherExpr (("MappedArguments", tok), [])
            | Some (definition, _, false) ->
                let left, _, _ = definition.G.fparams in
                let owner = Tok.unsafe_fake_tok (string_of_int (Tok.bytepos_of_tok left)) in
                G.OtherExpr (("Arguments", tok), [G.Name (G.Id ((name, tok), info)); G.Tk owner])
            | None -> G.N (G.Id ((name, tok), info))
          in
          Expressions.replace replacements expression kind)
    !special_uses;
  let mapper =
    object (self)
      inherit [_] G.map as super

      method! visit_directive () directive =
        let directive = super#visit_directive () directive in
        match directive.G.d with
        | G.ImportFrom (tok, source, imports) ->
            let imports =
              List.map
                (function
                  | id, None ->
                      ( id,
                        Option.map
                          (fun info -> (id, info))
                          (Hashtbl.find_opt import_bindings id) )
                  | imported -> imported)
                imports
            in
            { directive with G.d = G.ImportFrom (tok, source, imports) }
        | _ -> directive

      method! visit_expr () expression =
        match expression.G.e with
        | G.OtherExpr (("TypeParameters", _), G.E inner :: _) -> self#visit_expr () inner
        | _ ->
        match Expressions.find_opt replacements expression with
        | Some kind -> { expression with G.e = kind }
        | None -> super#visit_expr () expression
    end
  in
  mapper#visit_program () program
