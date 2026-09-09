module G = AST_generic
module T = Native_script_tree
module N = Tree_sitter_bindings.Tree_sitter_output_t

external create_parser : unit -> Tree_sitter_bindings.Tree_sitter_API.ts_parser = "octs_create_powershell_parser"
let parser = Domain.DLS.new_key create_parser

let identifier env node =
  let value = T.text env node in
  let length = String.length value in
  let value =
    if
      node.N.type_ = "variable" && length > 3
      && String.sub value 0 2 = "${"
      && value.[length - 1] = '}'
    then "$" ^ String.sub value 2 (length - 3)
    else value
  in
  let value =
    if
      env.T.pattern
      && String.length value > 1
      && value.[0] = '$'
      && String.uppercase_ascii value = value
    then value
    else String.lowercase_ascii value
  in
  (value, T.token env node)

let name env node = G.N (G.Id (identifier env node, G.empty_id_info ())) |> G.e

let wrappers =
  [
    "pipeline";
    "left_assignment_expression";
    "logical_expression";
    "bitwise_expression";
    "comparison_expression";
    "additive_expression";
    "multiplicative_expression";
    "format_expression";
    "range_expression";
    "array_literal_expression";
    "unary_expression";
    "string_literal";
    "member_name";
    "parenthesized_expression";
    "argument_expression";
    "logical_argument_expression";
    "bitwise_argument_expression";
    "comparison_argument_expression";
    "additive_argument_expression";
    "multiplicative_argument_expression";
    "format_argument_expression";
    "range_argument_expression";
    "integer_literal";
    "command_name_expr";
    "path_command_name";
    "sub_expression";
    "statement_list";
    "type_literal";
    "type_spec";
  ]

let string_bounds env node here =
  if here && node.N.end_pos.row <= node.N.start_pos.row + 1 then
    let position = N.{ row = node.end_pos.row; column = 0 } in
    (position, position)
  else if here then
    let row = node.N.end_pos.row - 1 in
    let line = env.T.src.Tree_sitter_run.Src_file.lines.(row) in
    let length = String.length line in
    let column =
      if length >= 2 && String.sub line (length - 2) 2 = "\r\n" then length - 2
      else if length > 0 && line.[length - 1] = '\n' then length - 1
      else length
    in
    (N.{ row = node.start_pos.row + 1; column = 0 }, N.{ row; column })
  else
    ( { node.N.start_pos with column = node.start_pos.column + 1 },
      { node.N.end_pos with column = node.end_pos.column - 1 } )

let decode_string ~expandable ~here value =
  let output = Buffer.create (String.length value) in
  let length = String.length value in
  let rec loop index =
    if index >= length then Some (Buffer.contents output)
    else if expandable && value.[index] = '`' then (
      if index + 1 >= length then None
      else
        match value.[index + 1] with
        | 'u' when index + 2 < length && value.[index + 2] = '{' -> None
        | '\n' -> loop (index + 2)
        | '\r' when index + 2 < length && value.[index + 2] = '\n' ->
            loop (index + 3)
        | c ->
            Buffer.add_char output
              (match c with
              | '0' -> '\000'
              | 'a' -> '\007'
              | 'b' -> '\b'
              | 'e' -> '\027'
              | 'f' -> '\012'
              | 'n' -> '\n'
              | 'r' -> '\r'
              | 't' -> '\t'
              | 'v' -> '\011'
              | c -> c);
            loop (index + 2))
    else if
      (not here)
      && index + 1 < length
      && value.[index] = value.[index + 1]
      && value.[index] = if expandable then '"' else '\''
    then (
      Buffer.add_char output value.[index];
      loop (index + 2))
    else (
      Buffer.add_char output value.[index];
      loop (index + 1))
  in
  loop 0

let string_literal env node ~expandable ~here =
  match decode_string ~expandable ~here (T.text env node) with
  | Some value -> T.literal env node value
  | None -> T.unsupported env node

let bare_argument env node =
  let value = T.text env node in
  let rec literal index =
    if index >= String.length value then true
    else match value.[index] with
      | '`' when index + 1 < String.length value -> literal (index + 2)
      | '$' | '\'' | '"' -> false
      | _ -> literal (index + 1)
  in
  if literal 0 then string_literal env node ~expandable:true ~here:true
  else T.unsupported env node

let rec expression env node =
  let parts = T.code_children node in
  match (node.N.type_, parts) with
  | "generic_token", _ -> bare_argument env node
  | "semgrep_ellipsis", _ when env.T.pattern ->
      G.Ellipsis (T.token env node) |> G.e
  | "variable", _
    when List.mem
           (String.lowercase_ascii (T.text env node))
           [ "$true"; "$false"; "$null" ] ->
      let literal =
        match String.lowercase_ascii (T.text env node) with
        | "$true" -> G.Bool (true, T.token env node)
        | "$false" -> G.Bool (false, T.token env node)
        | _ -> G.Null (T.token env node)
      in
      G.L literal |> G.e
  | ( ( "variable" | "command_name" | "function_name" | "simple_name"
      | "type_name" | "type_identifier" ),
      _ ) ->
      name env node
  | kind, [ inner ] when List.mem kind wrappers -> expression env inner
  | "pipeline_chain", first :: rest ->
      List.fold_left
        (fun input command ->
          let call = expression env command in
          match call.G.e with
          | G.Call (fn, (left, args, right)) ->
              G.Call
                ( fn,
                  ( left,
                    args @ [ G.ArgKwd (("|", T.token env command), input) ],
                    right ) )
              |> G.e
          | _ -> T.unsupported env node)
        (expression env first) rest
  | ( "command",
      ({ N.type_ = "command_invokation_operator"; _ } as operator) :: fn :: args
    ) ->
      if T.text env operator <> "&" then T.unsupported env node
      else
        G.Call
          ( expression env fn,
            T.bracket env node
              (command_arguments env (List.concat_map T.code_children args)) )
        |> G.e
  | "command", fn :: args ->
      G.Call
        ( name env fn,
          T.bracket env node
            (command_arguments env (List.concat_map T.code_children args)) )
      |> G.e
  | "assignment_expression", [ left; op; right ] when T.text env op = "=" ->
      T.assignment env node (expression env left) (expression env right)
  | "member_access", [ receiver; member ] ->
      G.DotAccess
        ( expression env receiver,
          T.punctuation env node ".",
          G.FN (G.Id (identifier env member, G.empty_id_info ())) )
      |> G.e
  | "element_access", [ receiver; index ] ->
      G.ArrayAccess
        (expression env receiver, T.bracket env node (expression env index))
      |> G.e
  | "invokation_expression", receiver :: member :: args ->
      let fn =
        G.DotAccess
          ( expression env receiver,
            T.punctuation env node ".",
            G.FN (G.Id (identifier env member, G.empty_id_info ())) )
        |> G.e
      in
      T.call env node fn (List.concat_map (method_arguments env) args)
  | ("verbatim_string_characters" | "verbatim_here_string_characters"), _ ->
      let here = node.N.type_ = "verbatim_here_string_characters" in
      let start_pos, end_pos = string_bounds env node here in
      string_literal env
        { node with N.start_pos; end_pos }
        ~expandable:false ~here
  | ("expandable_string_literal" | "expandable_here_string_literal"), _ ->
      expandable_string env node parts
  | ("decimal_integer_literal" | "hexadecimal_integer_literal"), _ ->
      G.L (G.Int (Parsed_int.parse (T.ident env node))) |> G.e
  | "array_literal_expression", _ ->
      G.Container (G.Array, T.bracket env node (List.map (expression env) parts))
      |> G.e
  | kind, [ left; right ] when List.mem kind wrappers -> (
      match T.operator env node with
      | Some op ->
          T.call env node
            (G.IdSpecial (G.Op op, T.token env node) |> G.e)
            [ expression env left; expression env right ]
      | None -> T.unsupported env node)
  | ("script_block" | "script_block_expression"), _ ->
      let parameters, body = function_body env node in
      G.Lambda
        {
          G.fkind = (G.LambdaKind, T.token env node);
          fparams = T.bracket env node parameters;
          frettype = None;
          fbody = G.FBStmt body;
        }
      |> G.e
  | _ -> T.unsupported env node

and expandable_string env node parts =
  let here = node.N.type_ = "expandable_here_string_literal" in
  let start_pos, end_pos = string_bounds env node here in
  let segment start_pos end_pos =
    if start_pos = end_pos then []
    else
      [
        string_literal env
          { node with N.start_pos; end_pos }
          ~expandable:true ~here;
      ]
  in
  let rec collect cursor = function
    | [] -> segment cursor end_pos
    | child :: rest ->
        segment cursor child.N.start_pos
        @ [ expression env child ]
        @ collect child.N.end_pos rest
  in
  match collect start_pos parts with
  | [] -> T.literal env node ""
  | [ part ] when parts = [] -> part
  | values -> T.concat env node values

and method_arguments env node =
  match node.N.type_ with
  | "argument_list" | "argument_expression_list" ->
      List.concat_map (method_arguments env) (T.code_children node)
  | _ -> [expression env node]

and command_arguments env nodes =
  let nodes = List.filter (fun node -> node.N.type_ <> "command_argument_sep") nodes in
  let key node =
    let raw, token = identifier env node in
    ("$" ^ String.sub raw 1 (String.length raw - 1), token)
  in
  let rec arguments = function
    | [] -> []
    | node :: value :: rest
      when node.N.type_ = "command_parameter" && value.N.type_ <> "command_parameter" ->
        G.ArgKwd (key node, expression env value) :: arguments rest
    | node :: rest when node.N.type_ = "command_parameter" ->
        G.ArgKwd (key node, T.unsupported env node) :: arguments rest
    | node :: rest -> G.Arg (expression env node) :: arguments rest
  in
  arguments nodes

and parameters env node =
  match node.N.type_ with
  | "script_parameter" -> (
      let parts = T.code_children node in
      match List.find_opt (fun child -> child.N.type_ = "variable") parts with
      | None ->
          ignore (T.unsupported env node);
          [ G.ParamEllipsis (T.token env node) ]
      | Some variable ->
          let pdefault =
            Option.bind
              (List.find_opt
                 (fun child -> child.N.type_ = "script_parameter_default")
                 parts)
              (fun default ->
                match T.code_children default with
                | [ value ] -> Some (expression env value)
                | _ -> Some (T.unsupported env default))
          in
          let ptype =
            Option.bind
              (List.find_opt
                 (fun child -> child.N.type_ = "attribute_list")
                 parts)
              (fun attributes ->
                let rec type_name node =
                  match (node.N.type_, T.code_children node) with
                  | "type_identifier", [] -> Some node
                  | _, [ child ] -> type_name child
                  | _ -> None
                in
                match type_name attributes with
                | Some name ->
                    Some
                      (G.TyN (G.Id (identifier env name, G.empty_id_info ()))
                      |> G.t)
                | None ->
                    ignore (T.unsupported env attributes);
                    None)
          in
          [
            G.Param
              {
                (G.param_of_id (identifier env variable)) with
                G.pdefault;
                ptype;
              };
          ])
  | _ -> List.concat_map (parameters env) (T.code_children node)

and function_body env node =
  let parts = T.code_children node in
  match (node.N.type_, parts) with
  | "script_block_expression", [ ({ N.type_ = "script_block"; _ } as inner) ] ->
      function_body env inner
  | _ ->
      let parameter_nodes, body =
        List.partition (fun child -> child.N.type_ = "param_block") parts
      in
      let parameters = List.concat_map (parameters env) parameter_nodes in
      (parameters, T.block env node (List.map (statement env) body))

and statement env node =
  let parts = T.code_children node in
  match (node.N.type_, parts) with
  | ("script_block" | "script_block_body" | "statement_block" | "statement_list"), _ ->
      T.block env node (List.map (statement env) parts)
  | "empty_statement", [] -> T.block env node []
  | "if_statement", condition :: yes :: clauses ->
      let rec otherwise = function
        | [] -> None
        | clause :: rest when clause.N.type_ = "elseif_clauses" ->
            otherwise (T.code_children clause @ rest)
        | clause :: rest when clause.N.type_ = "elseif_clause" -> (
            match T.code_children clause with
            | [condition; body] ->
                Some (G.If (T.token env clause, G.Cond (expression env condition),
                  statement env body, otherwise rest) |> G.s)
            | _ -> Some (G.exprstmt (T.unsupported env clause)))
        | [clause] when clause.N.type_ = "else_clause" -> (
            match T.code_children clause with
            | [body] -> Some (statement env body)
            | _ -> Some (G.exprstmt (T.unsupported env clause)))
        | clause :: _ -> Some (G.exprstmt (T.unsupported env clause))
      in
      G.If (T.token env node, G.Cond (expression env condition), statement env yes,
        otherwise clauses) |> G.s
  | "function_statement", name_ :: rest -> (
      let explicit, body =
        match rest with
        | [ body ] -> ([], Some body)
        | [ params; body ] -> (parameters env params, Some body)
        | [] -> ([], None)
        | _ -> ([], Some node)
      in
      match body with
      | Some body when body == node -> G.exprstmt (T.unsupported env node)
      | _ ->
          let embedded, body =
            match body with
            | Some body -> function_body env body
            | None -> ([], T.block env node [])
          in
          if explicit <> [] && embedded <> [] then
            G.exprstmt (T.unsupported env node)
          else
            G.DefStmt
              ( G.basic_entity (identifier env name_),
                G.FuncDef
                  {
                    G.fkind = (G.Function, T.token env node);
                    fparams = T.bracket env node (explicit @ embedded);
                    frettype = None;
                    fbody = G.FBStmt body;
                  } )
            |> G.s)
  | "flow_control_statement", []
    when List.exists
           (fun child -> String.lowercase_ascii (T.text env child) = "return")
           (T.children node) ->
      G.Return (T.token env node, None, G.sc) |> G.s
  | "flow_control_statement", [ value ]
    when List.exists
           (fun child -> String.lowercase_ascii (T.text env child) = "return")
           (T.children node) ->
      G.Return (T.token env node, Some (expression env value), G.sc) |> G.s
  | _ -> (
      let value = expression env node in
      if env.T.pattern then G.exprstmt value
      else
        match value.G.e with
        | G.Assign _ -> G.exprstmt value
        | _ -> G.exprstmt (G.Yield (T.token env node, Some value, false) |> G.e)
      )

let rec program env node =
  T.code_children node
  |> List.concat_map (fun child ->
         if child.N.type_ = "statement_list" then program env child
         else [ statement env child ])

let parse file = T.file parser program file
let parse_pattern source = T.pattern parser program source
