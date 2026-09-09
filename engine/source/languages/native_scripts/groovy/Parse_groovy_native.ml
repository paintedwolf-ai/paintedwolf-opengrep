module G = AST_generic
module T = Native_script_tree
module N = Tree_sitter_bindings.Tree_sitter_output_t

external create_parser : unit -> Tree_sitter_bindings.Tree_sitter_API.ts_parser = "octs_create_groovy_parser"
let parser = Domain.DLS.new_key create_parser

let rec expression env node =
  let parts = T.code_children node in
  match node.N.type_, parts with
  | "semgrep_ellipsis", _ when env.T.pattern -> G.Ellipsis (T.token env node) |> G.e
  | ("identifier" | "type_identifier"), _ -> T.name env node
  | "dotted_identifier", first :: rest ->
      List.fold_left (T.dot env node) (expression env first) rest
  | ("function_call" | "juxt_function_call"), [fn; args] ->
      T.call env node (expression env fn) (arguments env args)
  | "pipeline", [body] when body.N.type_ = "closure" ->
      let id = ("pipeline", T.punctuation env node "pipeline") in
      T.call env node (G.N (G.Id (id, G.empty_id_info ())) |> G.e) [expression env body]
  | "parenthesized_expression", [inner] -> expression env inner
  | "interpolation", [inner] -> expression env inner
  | "string_content", _ -> T.literal env node (T.text env node)
  | "string", _ ->
      if List.exists (fun part -> part.N.type_ = "interpolation") parts then
        T.concat env node (List.map (expression env) parts)
      else T.literal env node (String.concat "" (List.map (T.text env) parts))
  | "number_literal", _ -> number env node
  | "map", _ -> dictionary env node parts
  | "index", [receiver; index] ->
      G.ArrayAccess (expression env receiver, T.bracket env node (expression env index)) |> G.e
  | ("integer_literal" | "integer"), _ -> G.L (G.Int (Parsed_int.parse (T.ident env node))) |> G.e
  | "boolean_literal", _ -> G.L (G.Bool (T.text env node = "true", T.token env node)) |> G.e
  | "null", _ -> G.L (G.Null (T.token env node)) |> G.e
  | "list", _ -> G.Container (G.Array, T.bracket env node (List.map (expression env) parts)) |> G.e
  | "assignment", [left; right] -> T.assignment env node (expression env left) (expression env right)
  | "binary_op", [left; right] ->
      let operators = T.children node |> List.filter (fun n -> match n.N.kind with N.Literal _ -> true | _ -> false) in
      (match operators with
       | [operator] ->
           let op = match T.text env operator with
             | "+" -> Some G.Plus | "-" -> Some G.Minus | "*" -> Some G.Mult
             | "/" -> Some G.Div | "%" -> Some G.Mod | "**" -> Some G.Pow
             | "==" -> Some G.Eq | "!=" -> Some G.NotEq
             | "<" -> Some G.Lt | "<=" -> Some G.LtE | ">" -> Some G.Gt | ">=" -> Some G.GtE
             | "&&" -> Some G.And | "||" -> Some G.Or | _ -> None in
           (match op with
            | Some op -> T.call env node (G.IdSpecial (G.Op op, T.token env operator) |> G.e) [expression env left; expression env right]
            | None -> T.unsupported env node)
       | _ -> T.unsupported env node)
  | "closure", _ ->
      let params, body = match parts with
        | parameters :: body when parameters.N.type_ = "parameter_list" -> parameters_of env parameters, body
        | _ when List.exists (fun child -> T.text env child = "->") (T.children node) -> [], parts
        | _ -> [G.Param (G.param_of_id ("it", G.fake "it"))], parts in
      G.Lambda {G.fkind=(G.LambdaKind, T.token env node); fparams=T.bracket env node params; frettype=None;
                fbody=G.FBStmt (T.block env node (List.map (statement env) body))} |> G.e
  | _ -> T.unsupported env node

and number env node =
  let raw = T.text env node in
  let last = raw.[String.length raw - 1] in
  let hexadecimal = String.starts_with ~prefix:"0x" raw || String.starts_with ~prefix:"-0x" raw in
  let suffix = List.mem last ['G'; 'g'; 'I'; 'i'; 'L'; 'l']
    || (not hexadecimal && List.mem last ['D'; 'd'; 'F'; 'f']) in
  let value = if suffix then String.sub raw 0 (String.length raw - 1) else raw in
  let literal =
    if (not hexadecimal && String.contains value '.')
       || (not hexadecimal && List.mem last ['D'; 'd'; 'F'; 'f']) then
      G.Float (float_of_string_opt value, T.token env node)
    else G.Int (Parsed_int.parse_c_octal (value, T.token env node))
  in
  G.L literal |> G.e

and dictionary env node entries =
  let entry item =
    match T.code_children item with
    | [key; value] ->
        let key =
          if List.mem key.N.type_ ["identifier"; "type_identifier"] then
            T.literal env key (T.text env key)
          else expression env key
        in
        G.keyval key (T.punctuation env item ":") (expression env value)
    | _ -> T.unsupported env item
  in
  G.Container (G.Dict, T.bracket env node (List.map entry entries)) |> G.e

and arguments env node =
  let named, positional = List.partition (fun child -> child.N.type_ = "map_item") (T.code_children node) in
  let positional = List.map (expression env) positional in
  match named with
  | [] -> positional
  | _ -> dictionary env node named :: positional

and parameters_of env node =
  T.code_children node |> List.map (fun parameter ->
    match T.code_children parameter with
    | [id] -> T.parameter env id
    | [typ; id] -> G.Param {(G.param_of_id (T.ident env id)) with G.ptype=Some (G.TyN (G.Id (T.ident env typ, G.empty_id_info ())) |> G.t)}
    | _ -> ignore (T.unsupported env parameter); G.ParamEllipsis (T.token env parameter))

and statement env node =
  match node.N.type_, T.code_children node with
  | "closure", body -> T.block env node (List.map (statement env) body)
  | "function_definition", [id; params; body] ->
      T.function_definition env node id (parameters_of env params) (statement env body)
  | "function_definition", [typ; id; params; body]
      when List.mem typ.N.type_ ["identifier"; "type_identifier"]
           && params.N.type_ = "parameter_list" && body.N.type_ = "closure" ->
      let definition = {
        G.fkind=(G.Function, T.token env node);
        fparams=T.bracket env params (parameters_of env params);
        frettype=Some (G.TyN (G.Id (T.ident env typ, G.empty_id_info ())) |> G.t);
        fbody=G.FBStmt (statement env body)
      } in
      G.DefStmt (G.basic_entity (T.ident env id), G.FuncDef definition) |> G.s
  | "declaration", [id; value] -> T.declaration env node id (expression env value)
  | "declaration", [typ; id; value] ->
      let entity = G.basic_entity (T.ident env id) in
      G.DefStmt (entity, G.VarDef {G.vinit=Some (expression env value); vtype=Some (G.TyN (G.Id (T.ident env typ,G.empty_id_info ())) |> G.t); vtok=G.no_sc}) |> G.s
  | "return", values ->
      let value = match values with [] -> None | [value] -> Some (expression env value) | _ -> Some (T.unsupported env node) in
      G.Return (T.token env node, value, G.sc) |> G.s
  | "if_statement", condition :: yes :: rest ->
      let no = match rest with [] -> None | [value] -> Some (statement env value) | _ -> Some (G.exprstmt (T.unsupported env node)) in
      G.If (T.token env node, G.Cond (expression env condition), statement env yes, no) |> G.s
  | _ -> G.exprstmt (expression env node)

let program env node = T.code_children node |> List.map (statement env)
let parse file = T.file parser program file
let parse_pattern source = T.pattern parser program source
