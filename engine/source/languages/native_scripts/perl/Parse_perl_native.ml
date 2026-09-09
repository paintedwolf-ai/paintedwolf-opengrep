module G = AST_generic
module T = Native_script_tree
module N = Tree_sitter_bindings.Tree_sitter_output_t

external create_parser : unit -> Tree_sitter_bindings.Tree_sitter_API.ts_parser = "octs_create_perl_parser"
let parser = Domain.DLS.new_key create_parser

let variable_ident env node sigil =
  match T.code_children node with
  | [ variable ]
    when variable.N.type_ = "varname" && T.code_children variable = [] ->
      let name = T.text env variable in
      let value =
        if
          env.T.pattern && sigil <> "$"
          && String.uppercase_ascii name = name
          && not (String.contains name ':')
        then "$" ^ name
        else sigil ^ name
      in
      Some (value, T.token env node)
  | _ -> None

let variable env node sigil =
  match variable_ident env node sigil with
  | Some id -> G.N (G.Id (id, G.empty_id_info ())) |> G.e
  | None -> T.unsupported env node

let declaration env node identifiers value =
  let lexical = List.exists (fun child -> T.text env child = "my") (T.children node) in
  let scalar_pattern identifier =
    match identifier.N.type_ with
    | "scalar" -> Option.map (fun id -> G.PatId (id, G.empty_id_info ()))
        (variable_ident env identifier "$")
    | "undef_expression" -> Some (G.PatWildcard (T.token env identifier))
    | _ -> None
  in
  let definition entity value =
    G.DefStmt (entity, G.VarDef { G.vinit = value; vtype = None; vtok = G.no_sc }) |> G.s
  in
  if not lexical then G.exprstmt (T.unsupported env node)
  else match identifiers with
  | [identifier] when List.mem identifier.N.type_ ["array"; "hash"]
      || not (List.exists (fun child -> T.text env child = "(") (T.children node)) ->
      let sigil = match identifier.N.type_ with
        | "array" -> "@" | "hash" -> "%" | _ -> "$" in
      (match variable_ident env identifier sigil with
       | Some id ->
           let value = match value with
             | Some _ -> value
             | None ->
                 let initial = match identifier.N.type_ with
                   | "array" -> G.Container (G.Array, T.bracket env identifier [])
                   | "hash" -> G.Container (G.Dict, T.bracket env identifier [])
                   | _ -> G.L (G.Null (T.token env identifier)) in
                 Some (initial |> G.e) in
           definition (G.basic_entity id) value
       | None -> G.exprstmt (T.unsupported env node))
  | _ ->
      let patterns = List.filter_map scalar_pattern identifiers in
      if patterns = [] || List.length patterns <> List.length identifiers then
        G.exprstmt (T.unsupported env node)
      else
        let pattern = G.PatTuple (T.bracket env node patterns) in
        let value = match value with
          | Some _ -> value
          | None -> Some (G.Container (G.Tuple, T.bracket env node
              (List.map (fun id -> G.L (G.Null (T.token env id)) |> G.e) identifiers)) |> G.e)
        in
        definition { G.name = G.EPattern pattern; attrs = []; tparams = None } value

let ellipsis env node =
  if env.T.pattern then G.Ellipsis (T.token env node) |> G.e
  else (
    let error = Tree_sitter_run.Tree_sitter_error.create Error_node env.src node
        "Perl placeholder is only valid as a statement" in
    env.errors := error :: !(env.errors);
    env.skipped_tokens := Tok.unsafe_loc_of_tok (T.token env node) :: !(env.skipped_tokens);
    G.OtherExpr ((node.N.type_, T.token env node), []) |> G.e)

let assignment_operator env node =
  T.children node
  |> List.find_map (fun child ->
         let op = match T.text env child with
           | "=" -> Some G.Eq
           | ".=" -> Some G.Concat
           | "+=" -> Some G.Plus | "-=" -> Some G.Minus
           | "*=" -> Some G.Mult | "/=" -> Some G.Div
           | "%=" -> Some G.Mod | "**=" -> Some G.Pow
           | "<<=" -> Some G.LSL | ">>=" -> Some G.LSR
           | "&&=" -> Some G.And | "||=" -> Some G.Or
           | "//=" -> Some G.Nullish
           | _ -> None
         in
         Option.map (fun op -> (op, T.token env child)) op)

let rec expression env node =
  let parts = T.code_children node in
  match (node.N.type_, parts) with
  | "yadayada", _ -> ellipsis env node
  | ("function" | "bareword" | "package" | "method"), _ -> T.name env node
  | "scalar", _ -> variable env node "$"
  | "array", _ -> variable env node "@"
  | "hash", _ -> variable env node "%"
  | "number", _ ->
      let raw = T.text env node in
      let hexadecimal = String.starts_with ~prefix:"0x" raw in
      if not hexadecimal && (String.contains raw '.' || String.contains raw 'e' || String.contains raw 'E') then
        G.L (G.Float (float_of_string_opt raw, T.token env node)) |> G.e
      else G.L (G.Int (Parsed_int.parse_c_octal (T.ident env node))) |> G.e
  | "undef_expression", [] -> G.L (G.Null (T.token env node)) |> G.e
  | "autoquoted_bareword", _ -> T.literal env node (T.text env node)
  | "string_literal", _ -> string_value env node false parts
  | "interpolated_string_literal", _ -> string_value env node true parts
  | "command_string", _ ->
      let expandable =
        not
          (List.exists (fun child -> T.text env child = "'") (T.children node))
      in
      T.call env node
        (G.N (G.Id (("qx", T.punctuation env node "qx"), G.empty_id_info ()))
        |> G.e)
        [ string_value env node expandable parts ]
  | "string_content", _ -> string_content env node true
  | "parenthesized_expression", [ value ] -> expression env value
  | ( ("function_call_expression" | "ambiguous_function_call_expression"),
      fn :: args ) ->
      T.call env node (expression env fn) (arguments env args)
  | "method_call_expression", receiver :: method_ :: args ->
      T.call env node
        (T.dot env node (expression env receiver) method_)
        (arguments env args)
  | "eval_expression", [ body ] when body.N.type_ = "block" ->
      G.StmtExpr (statement env body) |> G.e
  | "eval_expression", [ value ] ->
      T.call env node
        (G.N
           (G.Id (("eval", T.punctuation env node "eval"), G.empty_id_info ()))
        |> G.e)
        [ expression env value ]
  | "assignment_expression", [ left; right ] -> (
      match (assignment_operator env node, left.N.type_, T.code_children left) with
      | Some (G.Eq, _), "variable_declaration", identifiers ->
          G.StmtExpr
            (declaration env left identifiers (Some (declaration_value env left right)))
          |> G.e
      | Some (G.Eq, _), _, _ ->
          T.assignment env node (expression env left)
            (assignment_value env left right)
      | Some operator, _, _ when left.N.type_ <> "variable_declaration" ->
          G.AssignOp (expression env left, operator, expression env right) |> G.e
      | _ -> T.unsupported env node)
  | "variable_declaration", identifiers ->
      G.StmtExpr (declaration env node identifiers None) |> G.e
  | "list_expression", _ ->
      G.Container (G.Tuple, T.bracket env node (List.map (expression env) parts))
      |> G.e
  | "anonymous_hash_expression", _ -> hash_literal env node parts
  | "anonymous_array_expression", _ ->
      G.Container (G.Array, T.bracket env node (arguments env parts)) |> G.e
  | ("binary_expression" | "lowprec_logical_expression"), [ left; right ] -> (
      let op =
        match List.find_opt (fun child ->
          List.mem (T.text env child) ["."; "//"]) (T.children node) with
        | Some child when T.text env child = "." -> Some G.Concat
        | Some _ -> Some G.Nullish
        | None ->
            T.children node |> List.find_map (fun child ->
              match child.N.kind, T.text env child with
              | N.Literal _, ("&&" | "and") -> Some G.And
              | N.Literal _, ("||" | "or") -> Some G.Or
              | _ -> None)
            |> (function Some _ as op -> op | None -> T.operator env node)
      in
      match op with
      | Some op ->
          T.call env node
            (G.IdSpecial (G.Op op, T.token env node) |> G.e)
            [ expression env left; expression env right ]
      | None -> T.unsupported env node)
  | ( (("array_element_expression" | "hash_element_expression") as kind),
      [ receiver; index ] ) ->
      let receiver =
        if receiver.N.type_ = "container_variable" then
          variable env receiver
            (if kind = "hash_element_expression" then "%" else "@")
        else expression env receiver
      in
      G.ArrayAccess (receiver, T.bracket env node (expression env index)) |> G.e
  | ("unary_expression" | "logical_not_expression"), [value]
    when List.exists (fun child -> List.mem (T.text env child) ["!"; "not"])
      (T.children node) ->
      T.call env node (G.IdSpecial (G.Op G.Not, T.token env node) |> G.e)
        [expression env value]
  | "conditional_expression", [condition; yes; no] ->
      G.Conditional (expression env condition, expression env yes, expression env no) |> G.e
  | "loopex_expression", [] ->
      let keyword = T.children node |> List.find_opt (fun child ->
        List.mem (T.text env child) ["last"; "next"]) in
      (match keyword with
       | Some keyword ->
           let tok = T.token env keyword in
           let statement = if T.text env keyword = "last" then
             G.Break (tok, G.LNone, G.sc) else G.Continue (tok, G.LNone, G.sc) in
           G.StmtExpr (statement |> G.s) |> G.e
       | None -> T.unsupported env node)
  | "return_expression", values ->
      G.StmtExpr
        (G.Return
           ( T.token env node,
             (match values with
             | [] -> None
             | [ v ] -> Some (expression env v)
             | _ -> Some (T.unsupported env node)),
             G.sc )
        |> G.s)
      |> G.e
  | _ -> T.unsupported env node

and condition_of env node condition =
  let value = expression env condition in
  match List.find_opt (fun child -> List.mem (T.text env child) ["unless"; "until"])
    (T.children node) with
  | Some keyword ->
      T.call env node (G.IdSpecial (G.Op G.Not, T.token env keyword) |> G.e) [value]
  | None -> value

and string_value env node expandable parts =
  let values =
    List.map (fun part -> string_content env part expandable) parts
  in
  match values with
  | [] -> T.literal env node ""
  | [ value ] -> value
  | _ -> T.concat env node values

and string_content env node expandable =
  let segment start_pos end_pos =
    if start_pos = end_pos then []
    else
      let part = { node with N.start_pos; end_pos } in
      [ T.literal env part (T.text env part) ]
  in
  let escaped child =
    let raw = T.text env child in
    if String.length raw <> 2 then T.unsupported env child
    else if child.N.type_ = "escaped_delimiter" then
      T.literal env child (String.make 1 raw.[1])
    else if not expandable then
      T.literal env child
        (if raw.[1] = '\\' || raw.[1] = '\'' then String.make 1 raw.[1] else raw)
    else
      match raw.[1] with
      | 'n' -> T.literal env child "\n"
      | 'r' -> T.literal env child "\r"
      | 't' -> T.literal env child "\t"
      | 'f' -> T.literal env child "\012"
      | 'b' -> T.literal env child "\b"
      | 'a' -> T.literal env child "\007"
      | 'e' -> T.literal env child "\027"
      | ('\\' | '$' | '@' | '\'' | '"') as value ->
          T.literal env child (String.make 1 value)
      | _ -> T.unsupported env child
  in
  let rec collect cursor = function
    | [] -> segment cursor node.N.end_pos
    | child :: rest ->
        let value =
          if List.mem child.N.type_ [ "escape_sequence"; "escaped_delimiter" ]
          then escaped child
          else if expandable then expression env child
          else T.literal env child (T.text env child)
        in
        segment cursor child.N.start_pos
        @ [ value ]
        @ collect child.N.end_pos rest
  in
  let values = collect node.N.start_pos (T.code_children node) in
  let literals =
    List.filter_map
      (fun value ->
        match value.G.e with
        | G.L (G.String (_, (text, _), _)) -> Some text
        | _ -> None)
      values
  in
  if List.length literals = List.length values then
    T.literal env node (String.concat "" literals)
  else
    match values with
    | [ value ] -> value
    | _ -> T.concat env node values

and hash_literal env node parts =
  let parts =
    List.concat_map
      (fun part ->
        if part.N.type_ = "list_expression" then T.code_children part
        else [ part ])
      parts
  in
  let rec pairs = function
    | [] -> []
    | key :: value :: rest ->
        G.keyval (expression env key)
          (T.punctuation env node "=>")
          (expression env value)
        :: pairs rest
    | [ _ ] -> [ T.unsupported env node ]
  in
  G.Container (G.Dict, T.bracket env node (pairs parts)) |> G.e

and declaration_value env declaration_node value =
  match T.code_children declaration_node with
  | [identifier] when List.mem identifier.N.type_ ["array"; "hash"]
      || not (List.exists (fun child -> T.text env child = "(")
      (T.children declaration_node)) -> assignment_value env identifier value
  | identifiers ->
      let converted = expression env value in
      (match converted.G.e with
       | G.Container (G.Tuple, (left, values, right)) ->
           let missing = max 0 (List.length identifiers - List.length values) in
           let padding = List.init missing (fun _ -> G.L (G.Null (T.token env value)) |> G.e) in
           {converted with G.e = G.Container (G.Tuple, (left, values @ padding, right))}
       | _ -> converted)

and assignment_value env identifier value =
  match (identifier.N.type_, value.N.type_) with
  | "hash", "list_expression" -> hash_literal env value (T.code_children value)
  | "array", "list_expression" ->
      G.Container
        ( G.Array,
          T.bracket env value
            (List.map (expression env) (T.code_children value)) )
      |> G.e
  | _ -> expression env value

and arguments env args =
  List.concat_map
    (fun node ->
      if node.N.type_ = "list_expression" then
        List.map (expression env) (T.code_children node)
      else [ expression env node ])
    args

and statement env node =
  match (node.N.type_, T.code_children node) with
  | "block", body -> T.block env node (List.map (statement env) body)
  | "block_statement", body ->
      G.DoWhile (T.token env node, T.block env node (List.map (statement env) body),
        G.L (G.Bool (false, T.token env node)) |> G.e) |> G.s
  | "loop_statement", [condition; body] ->
      G.While (T.token env node, G.Cond (condition_of env node condition),
        statement env body) |> G.s
  | ( "expression_statement",
      [ ({ N.type_ = "variable_declaration"; _ } as value) ] ) -> (
      declaration env value (T.code_children value) None)
  | "expression_statement", [ value ] -> (
      match (value.N.type_, T.code_children value) with
      | "yadayada", _ when not env.T.pattern ->
          G.exprstmt (T.unsupported env value)
      | "postfix_conditional_expression", [body; condition] ->
          G.If (T.token env value, G.Cond (condition_of env value condition),
            G.exprstmt (expression env body), None) |> G.s
      | "assignment_expression", [ left; right ] -> (
          match (left.N.type_, T.code_children left) with
          | "variable_declaration", identifiers
            when Option.map fst (assignment_operator env value) = Some G.Eq ->
              declaration env left identifiers (Some (declaration_value env left right))
          | _ -> G.exprstmt (expression env value))
      | _ -> G.exprstmt (expression env value))
  | "subroutine_declaration_statement", [ id; body ] ->
      T.function_definition env node id [] (statement env body)
  | "use_statement", module_ :: _ ->
      G.DirectiveStmt
        (G.d
           (G.ImportAll
              ( T.token env node,
                G.DottedName [ T.ident env module_ ],
                T.token env node )))
      |> G.s
  | "else", [body] -> statement env body
  | ("conditional_statement" | "elsif"), condition :: yes :: rest ->
      let no =
        match rest with
        | [] -> None
        | [ no ] -> Some (statement env no)
        | _ -> Some (G.exprstmt (T.unsupported env node))
      in
      G.If
        ( T.token env node,
          G.Cond (condition_of env node condition),
          statement env yes,
          no )
      |> G.s
  | _ -> G.exprstmt (expression env node)

let program env node = T.code_children node |> List.map (statement env)
let parse file = T.file parser program file
let parse_pattern source = T.pattern parser program source
