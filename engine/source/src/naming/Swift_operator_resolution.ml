module G = AST_generic

type scalar = Bool | String | Int | Float

type value_type =
  | Unknown
  | Unit
  | Scalar of scalar
  | Literal of scalar
  | Nil
  | Optional of value_type
  | Nominal of G.sid
  | Function of value_type list * value_type

type scope = {
  names : (string, binding) Hashtbl.t;
  outer : scope option;
  mutable generic_context : bool;
}

and binding =
  | Value of value_type
  | Type of value_type
  | Alias of G.type_ * scope
  | Functions of signature list
  | Shadow

and signature = {
  name : G.name;
  definition : G.function_definition;
  scope : scope;
  generic : bool;
}

type state = {
  operators : (string, signature list) Hashtbl.t;
  mutable opaque_imports : bool;
  mutable classes : (G.class_definition * scope) list;
}

type compatibility = Incompatible | Uncertain | Compatible of int

let frame outer =
  {
    names = Hashtbl.create 16;
    outer;
    generic_context =
      Option.fold ~none:false ~some:(fun scope -> scope.generic_context) outer;
  }

let rec lookup scope name =
  match Hashtbl.find_opt scope.names name with
  | Some _ as found -> found
  | None -> Option.bind scope.outer (fun scope -> lookup scope name)

let name_path = function
  | G.Id ((name, _), _) -> Some [ name ]
  | G.IdQualified { name_middle; name_last = (name, _), None; _ } -> (
      match name_middle with
      | None -> Some [ name ]
      | Some (G.QDots path)
        when List.for_all (fun (_, args) -> Option.is_none args) path ->
          Some (List.map (fun ((part, _), _) -> part) path @ [ name ])
      | _ -> None)
  | _ -> None

let builtin = function
  | "Void" -> Unit
  | "Bool" -> Scalar Bool
  | "String" -> Scalar String
  | "Int" -> Scalar Int
  | "Double"
  | "Float" ->
      Scalar Float
  | _ -> Unknown

let rec type_ state scope depth value =
  if depth > 16 then Unknown
  else
    match value.G.t with
    | G.TyTuple (_, [], _)
    | G.TyRecordAnon (_, (_, [], _)) ->
        Unit
    | G.TyQuestion (value, _) -> Optional (type_ state scope (depth + 1) value)
    | G.TyN name -> (
        match name_path name with
        | Some [ name ] -> (
            match lookup scope name with
            | Some (Type value) -> value
            | Some (Alias (value, declaration_scope)) ->
                type_ state declaration_scope (depth + 1) value
            | Some _ -> Unknown
            | None when not state.opaque_imports -> builtin name
            | None -> Unknown)
        | Some [ "Swift"; name ] when Option.is_none (lookup scope "Swift") ->
            builtin name
        | _ -> Unknown)
    | G.TyFun (parameters, result) ->
        let parameters =
          List.map
            (function
              | G.Param parameter ->
                  Option.fold ~none:Unknown
                    ~some:(type_ state scope (depth + 1))
                    parameter.G.ptype
              | _ -> Unknown)
            parameters
        in
        Function (parameters, type_ state scope (depth + 1) result)
    | _ -> Unknown

let rec normalized = function
  | Literal scalar -> Scalar scalar
  | Optional value -> Optional (normalized value)
  | value -> value

let same left right = normalized left = normalized right

let rec compatible expected actual =
  match (expected, actual) with
  | Unknown, _
  | _, Unknown ->
      Uncertain
  | Optional _, Nil -> Compatible 0
  | Optional expected, Optional actual -> compatible expected actual
  | Optional expected, actual -> (
      match compatible expected actual with
      | Compatible cost -> Compatible (cost + 1)
      | other -> other)
  | Nominal _, Literal _ -> Uncertain
  | expected, actual when same expected actual -> Compatible 0
  | _ -> Incompatible

let autoclosure parameter =
  let attributes =
    parameter.G.pattrs
    @ Option.fold ~none:[] ~some:(fun typ -> typ.G.t_attrs) parameter.G.ptype
  in
  List.exists
    (function
      | G.NamedAttr (_, G.Id (("@autoclosure", _), _), _) -> true
      | _ -> false)
    attributes

let combine left right =
  match (left, right) with
  | Incompatible, _
  | _, Incompatible ->
      Incompatible
  | Uncertain, _
  | _, Uncertain ->
      Uncertain
  | Compatible left, Compatible right -> Compatible (left + right)

let signature_arguments state signature actuals =
  let parameters = Tok.unbracket signature.definition.G.fparams in
  if signature.generic then (Uncertain, [])
  else if List.length parameters <> List.length actuals then (Incompatible, [])
  else
    List.fold_left2
      (fun (matched, modes) parameter actual ->
        match parameter with
        | G.Param parameter ->
            let expected =
              Option.fold ~none:Unknown
                ~some:(type_ state signature.scope 0)
                parameter.G.ptype
            in
            let expected, mode, cost =
              if autoclosure parameter then
                match expected with
                | Function ([], result) -> (result, G.AutoclosureArgument, 1)
                | _ -> (Unknown, G.AutoclosureArgument, 1)
              else (expected, G.EagerArgument, 0)
            in
            let result =
              match compatible expected actual with
              | Compatible value -> Compatible (value + cost)
              | other -> other
            in
            (combine matched result, modes @ [ mode ])
        | _ -> (combine matched Uncertain, modes @ [ G.EagerArgument ]))
      (Compatible 0, []) parameters actuals

let operator_name = function
  | G.And -> Some "&&"
  | G.Or -> Some "||"
  | G.Not -> Some "!"
  | G.Eq -> Some "=="
  | G.NotEq -> Some "!="
  | G.PhysEq -> Some "==="
  | G.NotPhysEq -> Some "!=="
  | G.Lt -> Some "<"
  | G.LtE -> Some "<="
  | G.Gt -> Some ">"
  | G.GtE -> Some ">="
  | _ -> None

let native_operator operator actuals =
  let bool value = compatible (Scalar Bool) value in
  match (operator, actuals) with
  | (G.And | G.Or), [ left; right ] ->
      (combine (bool left) (combine (Compatible 1) (bool right)), Scalar Bool)
  | G.Not, [ value ] -> (bool value, Scalar Bool)
  | (G.Eq | G.NotEq), [ left; right ] -> (
      match (normalized left, normalized right) with
      | Scalar left, Scalar right when left = right ->
          (Compatible 0, Scalar Bool)
      | Optional (Scalar _), Nil
      | Nil, Optional (Scalar _) ->
          (Compatible 0, Scalar Bool)
      | Optional (Scalar left), Optional (Scalar right) when left = right ->
          (Compatible 0, Scalar Bool)
      | Unknown, _
      | _, Unknown ->
          (Uncertain, Unknown)
      | _ -> (Incompatible, Unknown))
  | (G.Lt | G.LtE | G.Gt | G.GtE), [ left; right ] -> (
      match (normalized left, normalized right) with
      | Scalar ((String | Int | Float) as left), Scalar right when left = right
        ->
          (Compatible 0, Scalar Bool)
      | Unknown, _
      | _, Unknown ->
          (Uncertain, Unknown)
      | _ -> (Incompatible, Unknown))
  | _ -> (Uncertain, Unknown)

let resolved_return state signature =
  Option.fold ~none:Unknown
    ~some:(type_ state signature.scope 0)
    signature.definition.G.frettype

let rec expression state scope value =
  match value.G.e with
  | G.L (G.Bool _) -> Literal Bool
  | G.L (G.String _) -> Literal String
  | G.L (G.Int _) -> Literal Int
  | G.L (G.Float _) -> Literal Float
  | G.L (G.Null _) -> Nil
  | G.N (G.Id ((name, _), _)) -> (
      match lookup scope name with
      | Some (Value value) -> value
      | _ -> Unknown)
  | G.Cast (typ, _, _) -> type_ state scope 0 typ
  | G.Call ({ e = G.IdSpecial (G.Op operator, _); _ }, (_, arguments, _))
    when Option.is_some (operator_name operator) ->
      let actuals = List.map (argument state scope) arguments in
      let spelling = Option.get (operator_name operator) in
      let declared =
        Option.value ~default:[] (Hashtbl.find_opt state.operators spelling)
      in
      let candidates =
        List.map
          (fun signature ->
            let matching, modes = signature_arguments state signature actuals in
            ( matching,
              G.DeclaredOperator (signature.name, modes),
              resolved_return state signature ))
          declared
      in
      let native, result = native_operator operator actuals in
      let candidates = (native, G.NativeOperator, result) :: candidates in
      let result, resolution =
        if
          state.opaque_imports
          || List.exists
               (fun (matching, _, _) -> matching = Uncertain)
               candidates
        then (Unknown, G.UnresolvedOperator)
        else
          let matching =
            List.filter_map
              (function
                | Compatible cost, resolution, result ->
                    Some (cost, resolution, result)
                | _ -> None)
              candidates
            |> List.sort (fun (left, _, _) (right, _, _) ->
                Int.compare left right)
          in
          match matching with
          | (cost, resolution, result) :: rest
            when not (List.exists (fun (other, _, _) -> other = cost) rest) ->
              (result, resolution)
          | _ -> (Unknown, G.UnresolvedOperator)
      in
      value.operator_resolution <- Some resolution;
      result
  | G.Call ({ e = G.N (G.Id ((name, _), _)); _ }, (_, arguments, _)) -> (
      let actuals = List.map (argument state scope) arguments in
      match lookup scope name with
      | Some (Type value) -> value
      | Some (Alias (typ, declaration_scope)) ->
          type_ state declaration_scope 0 typ
      | Some (Functions functions) -> (
          let candidates =
            List.filter
              (fun signature ->
                fst (signature_arguments state signature actuals)
                <> Incompatible)
              functions
          in
          match candidates with
          | [ signature ] -> resolved_return state signature
          | _ -> Unknown)
      | Some (Value (Function (_, result))) -> result
      | _ -> Unknown)
  | G.OtherExpr (("Try", _), [ G.E value ]) -> expression state scope value
  | _ -> Unknown

and argument state scope = function
  | G.Arg value
  | G.ArgKwd (_, value) ->
      expression state scope value
  | _ -> Unknown

let declaration_name entity =
  match entity.G.name with
  | G.EN name -> Some name
  | _ -> None

let simple = function
  | G.Id ((name, _), _) -> Some name
  | _ -> None

let add_function state scope entity definition =
  match declaration_name entity with
  | Some name -> (
      match simple name with
      | Some spelling ->
          let signature =
            {
              name;
              definition;
              scope;
              generic = scope.generic_context || Option.is_some entity.G.tparams;
            }
          in
          let current =
            match Hashtbl.find_opt scope.names spelling with
            | Some (Functions current) -> current
            | _ -> []
          in
          Hashtbl.replace scope.names spelling
            (Functions (signature :: current));
          if
            List.exists
              (fun op -> operator_name op = Some spelling)
              [
                G.And;
                G.Or;
                G.Not;
                G.Eq;
                G.NotEq;
                G.PhysEq;
                G.NotPhysEq;
                G.Lt;
                G.LtE;
                G.Gt;
                G.GtE;
              ]
          then
            let existing =
              Option.value ~default:[]
                (Hashtbl.find_opt state.operators spelling)
            in
            Hashtbl.replace state.operators spelling (signature :: existing)
      | None -> ())
  | None -> ()

let extension definition =
  Tok.content_of_tok (snd definition.G.ckind) = "extension"

let members definition =
  List.map (fun (G.F statement) -> statement) (Tok.unbracket definition.G.cbody)

let rec predeclare state scope statements =
  List.iter
    (fun statement ->
      match statement.G.s with
      | G.DefStmt (entity, G.FuncDef definition) ->
          add_function state scope entity definition
      | G.DefStmt
          ({ name = G.EN (G.Id ((name, _), info)); _ }, G.ClassDef definition)
        when not (extension definition) ->
          let identity =
            match !(info.G.id_resolved) with
            | Some (_, sid) -> sid
            | None -> G.SId.mk ()
          in
          Hashtbl.replace scope.names name (Type (Nominal identity))
      | G.DefStmt
          ( { name = G.EN (G.Id ((name, _), _)); _ },
            G.TypeDef { tbody = G.AliasType typ } ) ->
          Hashtbl.replace scope.names name (Alias (typ, scope))
      | G.DefStmt (_, G.ClassDef _) -> ()
      | G.DefStmt ({ name = G.EN (G.Id ((name, _), _)); _ }, _) ->
          Hashtbl.replace scope.names name Shadow
      | G.DirectiveStmt { d = G.ImportAll _ | G.ImportAs _ | G.ImportFrom _; _ }
        ->
          state.opaque_imports <- true
      | _ -> ())
    statements;
  List.iter
    (fun statement ->
      match statement.G.s with
      | G.DefStmt (entity, G.ClassDef definition) ->
          let local = frame (Some scope) in
          local.generic_context <-
            local.generic_context || Option.is_some entity.G.tparams;
          let self_type =
            Option.fold ~none:Unknown
              ~some:(fun name -> type_ state scope 0 (G.TyN name |> G.t))
              (declaration_name entity)
          in
          Hashtbl.replace local.names "Self" (Type self_type);
          state.classes <- (definition, local) :: state.classes;
          predeclare state local (members definition)
      | _ -> ())
    statements

let resolve_program program =
  let state =
    { operators = Hashtbl.create 8; opaque_imports = false; classes = [] }
  in
  let module_scope = frame None in
  predeclare state module_scope program;
  let visitor =
    object (self)
      inherit [_] G.iter_no_id_info as super

      method! visit_expr scope value =
        (match value.G.e with
        | G.Call
            (({ e = G.N (G.Id ((name, _), _)); _ } as callee), (_, arguments, _))
          ->
            let actuals = List.map (argument state scope) arguments in
            let parameters =
              match lookup scope name with
              | Some (Functions functions) -> (
                  let candidates =
                    List.filter
                      (fun signature ->
                        (not signature.generic)
                        && fst (signature_arguments state signature actuals)
                           <> Incompatible)
                      functions
                  in
                  match candidates with
                  | [ signature ] ->
                      List.map
                        (function
                          | G.Param parameter ->
                              Option.fold ~none:Unknown
                                ~some:(type_ state signature.scope 0)
                                parameter.G.ptype
                          | _ -> Unknown)
                        (Tok.unbracket signature.definition.G.fparams)
                  | _ -> [])
              | Some (Value (Function (parameters, _))) -> parameters
              | _ -> []
            in
            self#visit_expr scope callee;
            if List.length parameters = List.length arguments then
              List.iter2
                (fun expected argument ->
                  match argument with
                  | G.Arg { e = G.Lambda definition; _ }
                  | G.ArgKwd (_, { e = G.Lambda definition; _ }) ->
                      self#visit_contextual_function scope (Some expected)
                        definition
                  | _ -> self#visit_argument scope argument)
                parameters arguments
            else List.iter (self#visit_argument scope) arguments
        | _ -> super#visit_expr scope value);
        ignore (expression state scope value)

      method! visit_function_definition scope definition =
        self#visit_contextual_function scope None definition

      method private visit_contextual_function scope expected definition =
        let expected_parameters, expected_result =
          match expected with
          | Some (Function (parameters, result)) -> (parameters, result)
          | _ -> ([], Unknown)
        in
        let returns_value =
          match definition.G.frettype with
          | None ->
              fst definition.G.fkind = G.LambdaKind && expected_result <> Unit
          | Some typ -> type_ state scope 0 typ <> Unit
        in
        (match definition.G.fbody with
        | G.FBStmt
            { s = G.Block (_, [ { s = G.ExprStmt (value, _); _ } ], _); _ }
        | G.FBExpr value ->
            value.G.is_implicit_return <- returns_value
        | _ -> ());
        let local = frame (Some scope) in
        List.iteri
          (fun index parameter ->
            match parameter with
            | G.Param parameter ->
                Option.iter
                  (fun (name, _) ->
                    let value =
                      match parameter.G.ptype with
                      | Some typ -> type_ state scope 0 typ
                      | None ->
                          Option.value ~default:Unknown
                            (List.nth_opt expected_parameters index)
                    in
                    Hashtbl.replace local.names name (Value value))
                  parameter.G.pname
            | _ -> ())
          (Tok.unbracket definition.G.fparams);
        self#visit_function_body local definition.G.fbody

      method! visit_stmt scope statement =
        match statement.G.s with
        | G.Block (_, statements, _) ->
            let local = frame (Some scope) in
            predeclare state local statements;
            List.iter (self#visit_stmt local) statements
        | G.DefStmt (_, G.ClassDef definition) ->
            let local =
              match
                List.find_opt
                  (fun (candidate, _) -> candidate == definition)
                  state.classes
              with
              | Some (_, scope) -> scope
              | None -> frame (Some scope)
            in
            List.iter (self#visit_stmt local) (members definition)
        | G.DefStmt (_entity, G.FuncDef definition) ->
            self#visit_function_definition scope definition
        | G.DefStmt
            ({ name = G.EN (G.Id ((name, _), _)); _ }, G.VarDef definition) ->
            (match (definition.G.vinit, definition.G.vtype) with
            | Some { e = G.Lambda closure; _ }, Some typ ->
                self#visit_contextual_function scope
                  (Some (type_ state scope 0 typ))
                  closure
            | value, _ -> Option.iter (self#visit_expr scope) value);
            let value =
              match definition.G.vtype with
              | Some typ -> type_ state scope 0 typ
              | None ->
                  Option.fold ~none:Unknown ~some:(expression state scope)
                    definition.G.vinit
            in
            Hashtbl.replace scope.names name (Value (normalized value))
        | _ -> super#visit_stmt scope statement
    end
  in
  List.iter (visitor#visit_stmt module_scope) program;
  program
