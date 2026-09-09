module G = AST_generic
module N = Tree_sitter_bindings.Tree_sitter_output_t
module T = Native_script_tree
module R = Scheme_reader

external create_parser : unit -> Tree_sitter_bindings.Tree_sitter_API.ts_parser
  = "octs_create_scheme_parser"

let parser = Domain.DLS.new_key create_parser

type context = { tree : T.env; bound : string list; macros : string list }

let bind ctx nodes =
  let names = List.filter_map (R.symbol ctx.tree) nodes in
  {
    ctx with
    bound = names @ ctx.bound;
    macros = List.filter (fun name -> not (List.mem name names)) ctx.macros;
  }

let parts = T.code_children
let symbol ctx node = R.symbol ctx.tree node
let unsupported ctx node = T.unsupported ctx.tree node

let sequence ctx node values =
  match values with
  | [] -> G.L (G.Unit (T.token ctx.tree node)) |> G.e
  | [ value ] -> value
  | values -> G.Seq values |> G.e

let rec expression ctx node =
  let env = ctx.tree in
  match node.N.type_ with
  | "symbol" when env.pattern && T.text env node = "..." ->
      G.Ellipsis (T.token env node) |> G.e
  | "symbol" -> R.name env node
  | "list" -> form ctx node (parts node)
  | "quote" -> (
      match parts node with
      | [ value ] -> R.quoted env value
      | _ -> unsupported ctx node)
  | "quasiquote" -> (
      match parts node with
      | [ value ] -> quasiquote ctx 1 value
      | _ -> unsupported ctx node)
  | "vector"
  | "byte_vector" ->
      R.quoted env node
  | _ -> (
      match R.atom env node with
      | Some literal -> G.L literal |> G.e
      | None -> unsupported ctx node)

and quasiquote ctx depth node =
  let env = ctx.tree in
  let data children =
    G.Container (G.List, T.bracket env node children) |> G.e
  in
  let dispatch kind value =
    match kind with
    | "unquote"
    | "unquote-splicing"
      when depth = 1 ->
        expression ctx value
    | "unquote"
    | "unquote-splicing" ->
        data [ quasiquote ctx (depth - 1) value ]
    | "quasiquote" -> data [ quasiquote ctx (depth + 1) value ]
    | _ -> unsupported ctx node
  in
  match (node.N.type_, parts node) with
  | (("unquote" | "unquote_splicing" | "quasiquote") as kind), [ value ] ->
      dispatch
        (if kind = "unquote_splicing" then "unquote-splicing" else kind)
        value
  | "list", [ head; value ]
    when List.mem (T.text env head)
           [ "unquote"; "unquote-splicing"; "quasiquote" ] ->
      dispatch (T.text env head) value
  | ("list" | "vector"), children ->
      data (List.map (quasiquote ctx depth) children)
  | _ -> R.quoted env node

and parameters ctx node nodes =
  let env = ctx.tree in
  let rec loop = function
    | [] -> Some []
    | [ dot; rest ] when T.text env dot = "." ->
        Option.map
          (fun id -> [ G.ParamRest (T.token env dot, G.param_of_id id) ])
          (R.identifier env rest)
    | parameter :: rest ->
        let param =
          match symbol ctx parameter with
          | Some "..." when env.pattern ->
              Some (G.ParamEllipsis (T.token env parameter))
          | Some "." -> None
          | Some _ ->
              Option.map
                (fun id -> G.Param (G.param_of_id id))
                (R.identifier env parameter)
          | None -> None
        in
        Option.bind param (fun param ->
            Option.map (fun rest -> param :: rest) (loop rest))
  in
  if node.N.type_ = "symbol" then
    Option.map
      (fun id -> [ G.ParamRest (T.token env node, G.param_of_id id) ])
      (R.identifier env node)
  else loop nodes

and function_ ctx node parameter_node nodes body =
  Option.map
    (fun params ->
      let scoped =
        bind ctx
          (if parameter_node.N.type_ = "symbol" then [ parameter_node ]
           else nodes)
      in
      {
        G.fkind = (G.Function, T.token ctx.tree node);
        fparams = T.bracket ctx.tree parameter_node params;
        frettype = None;
        fbody = G.FBExpr (body_expr scoped node body);
      })
    (parameters ctx parameter_node nodes)

and body_expr ctx node body =
  let ctx = predeclare ctx body in
  sequence ctx node (List.map (expression ctx) body)

and predeclare ctx body =
  List.fold_left
    (fun ctx node ->
      match (node.N.type_, parts node) with
      | "list", head :: name :: _ when T.text ctx.tree head = "define" -> (
          match (name.N.type_, parts name) with
          | "symbol", _ -> bind ctx [ name ]
          | "list", name :: _ -> bind ctx [ name ]
          | _ -> ctx)
      | "list", head :: name :: _
        when List.mem (T.text ctx.tree head)
               [ "define-syntax"; "define-macro"; "defmacro" ] -> (
          let name =
            if name.N.type_ = "list" then
              match parts name with
              | first :: _ -> Some first
              | [] -> None
            else Some name
          in
          match Option.bind name (symbol ctx) with
          | Some name -> { ctx with macros = name :: ctx.macros }
          | None -> ctx)
      | _ -> ctx)
    ctx body

and bindings ctx node sequential binding_node body =
  let env = ctx.tree in
  let pairs =
    List.filter_map
      (fun binding ->
        match (binding.N.type_, parts binding) with
        | "list", [ name; value ] when Option.is_some (symbol ctx name) ->
            Some (name, value)
        | _ -> None)
      (parts binding_node)
  in
  if
    binding_node.N.type_ <> "list"
    || List.length pairs <> List.length (parts binding_node)
  then unsupported ctx node
  else
    let pattern name =
      G.PatId (Option.get (R.identifier env name), G.empty_id_info ())
    in
    let body scoped = G.exprstmt (body_expr scoped node body) in
    let statements =
      if sequential then
        let rec nested ctx = function
          | [] -> body ctx
          | (name, value) :: rest ->
              let declaration =
                G.LetPattern (pattern name, expression ctx value)
                |> G.e |> G.exprstmt
              in
              T.block env node [ declaration; nested (bind ctx [ name ]) rest ]
        in
        [ nested ctx pairs ]
      else
        let names, values = List.split pairs in
        let declaration =
          G.LetPattern
            ( G.PatTuple (T.bracket env binding_node (List.map pattern names)),
              G.Container
                ( G.Tuple,
                  T.bracket env binding_node (List.map (expression ctx) values)
                )
              |> G.e )
          |> G.e |> G.exprstmt
        in
        [ declaration; body (bind ctx names) ]
    in
    T.block env node statements |> G.stmt_to_expr

and form ctx node nodes =
  let env = ctx.tree in
  let tok = T.token env node in
  let call head args =
    T.call env node (expression ctx head) (List.map (expression ctx) args)
  in
  match nodes with
  | [] -> unsupported ctx node
  | head :: args -> (
      let head_name = Option.value ~default:"" (symbol ctx head) in
      if List.mem head_name ctx.macros then unsupported ctx node
      else if List.mem head_name ctx.bound then call head args
      else
        match (head_name, args) with
        | "quote", [ value ] -> R.quoted env value
        | "quasiquote", [ value ] -> quasiquote ctx 1 value
        | "lambda", params :: body -> (
            match function_ ctx node params (parts params) body with
            | Some fn -> G.Lambda fn |> G.e
            | None -> unsupported ctx node)
        | "define", name :: body -> (
            match (name.N.type_, parts name, body) with
            | "symbol", _, [ value ] when Option.is_some (R.identifier env name)
              ->
                G.DefStmt
                  ( G.basic_entity (Option.get (R.identifier env name)),
                    G.VarDef
                      {
                        G.vinit = Some (expression ctx value);
                        vtype = None;
                        vtok = G.no_sc;
                      } )
                |> G.s |> G.stmt_to_expr
            | "list", name_ :: params, body -> (
                match
                  (R.identifier env name_, function_ ctx node name params body)
                with
                | Some id, Some fn ->
                    G.DefStmt (G.basic_entity id, G.FuncDef fn)
                    |> G.s |> G.stmt_to_expr
                | _ -> unsupported ctx node)
            | _ -> unsupported ctx node)
        | (("let" | "let*") as form), bindings_ :: body ->
            bindings ctx node (form = "let*") bindings_ body
        | "begin", body -> body_expr ctx node body
        | "if", [ condition; yes; no ] ->
            G.Conditional
              (expression ctx condition, expression ctx yes, expression ctx no)
            |> G.e
        | "if", [ condition; yes ] ->
            G.If
              ( tok,
                G.Cond (expression ctx condition),
                G.exprstmt (expression ctx yes),
                None )
            |> G.s |> G.stmt_to_expr
        | "set!", [ name; value ] when Option.is_some (symbol ctx name) ->
            G.Assign (R.name env name, tok, expression ctx value) |> G.e
        | (("and" | "or") as op), values -> (
            match values with
            | [] -> G.L (G.Bool (op = "and", tok)) |> G.e
            | [ value ] -> expression ctx value
            | _ ->
                T.call env node
                  (G.IdSpecial
                     ( G.Op (if op = "and" then G.And else G.Or),
                       T.token env head )
                  |> G.e)
                  (List.map (expression ctx) values))
        | "use-modules", modules ->
            T.block env node
              (List.concat_map (Scheme_imports.import env) modules)
            |> G.stmt_to_expr
        | ( ( "if" | "define" | "lambda" | "quote" | "quasiquote" | "set!"
            | "let" | "let*" | "define-library" | "library" | "import"
            | "include" | "include-ci" | "cond-expand" | "define-syntax"
            | "syntax-rules" | "syntax-case" | "let-syntax" | "letrec-syntax"
            | "define-macro" | "defmacro" | "letrec" | "letrec*" | "do" | "cond"
            | "case" | "define*" | "lambda*" | "define-module" | "eval-when"
            | "with-fluids" | "unquote" | "unquote-splicing" | "syntax"
            | "quasisyntax" ),
            _ ) ->
            unsupported ctx node
        | _ -> call head args)

let program env node =
  let nodes = parts node in
  let ctx = predeclare { tree = env; bound = []; macros = [] } nodes in
  let rec reader_directives node =
    if node.N.type_ = "directive" then [ node ]
    else if T.comment node then []
    else List.concat_map reader_directives (T.children node)
  in
  let directives = reader_directives node in
  if directives <> [] then
    List.map
      (fun directive -> G.exprstmt (unsupported ctx directive))
      directives
  else
    List.concat_map
      (fun node ->
        match (node.N.type_, parts node) with
        | "list", head :: modules when T.text env head = "use-modules" ->
            List.concat_map (Scheme_imports.import env) modules
        | _ -> (
            let value = expression ctx node in
            match value.G.e with
            | G.StmtExpr statement -> [ statement ]
            | _ -> [ G.exprstmt value ]))
      nodes

let parse file = T.file parser program file
let parse_pattern source = T.pattern parser program source
