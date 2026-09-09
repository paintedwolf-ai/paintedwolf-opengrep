module G = AST_generic
module N = Tree_sitter_bindings.Tree_sitter_output_t
module T = Native_script_tree

let decode text =
  let output = Buffer.create (String.length text) in
  let rec loop i =
    if i = String.length text then Some (Buffer.contents output)
    else if text.[i] <> '\\' then (
      Buffer.add_char output text.[i];
      loop (i + 1))
    else if i + 1 = String.length text then None
    else
      match text.[i + 1] with
      | 'x'
      | 'X' -> (
          match String.index_from_opt text (i + 2) ';' with
          | None -> None
          | Some finish -> (
              let digits = String.sub text (i + 2) (finish - i - 2) in
              match int_of_string_opt ("0x" ^ digits) with
              | Some scalar when Uchar.is_valid scalar ->
                  Buffer.add_utf_8_uchar output (Uchar.of_int scalar);
                  loop (finish + 1)
              | _ -> None))
      | c -> (
          let value =
            match c with
            | 'a' -> Some '\007'
            | 'b' -> Some '\b'
            | 't' -> Some '\t'
            | 'n' -> Some '\n'
            | 'r' -> Some '\r'
            | 'v' -> Some '\011'
            | 'f' -> Some '\012'
            | '"'
            | '\\'
            | '|' ->
                Some c
            | _ -> None
          in
          match value with
          | None -> None
          | Some c ->
              Buffer.add_char output c;
              loop (i + 2))
  in
  loop 0

let symbol env node =
  if node.N.type_ <> "symbol" then None
  else
    let raw = T.text env node in
    if String.length raw >= 2 && raw.[0] = '|' then
      decode (String.sub raw 1 (String.length raw - 2))
    else Some raw

let identifier env node =
  Option.map (fun name -> (name, T.token env node)) (symbol env node)

let name env node =
  match identifier env node with
  | Some id -> G.N (G.Id (id, G.empty_id_info ())) |> G.e
  | None -> T.unsupported env node

let atom env node =
  let tok = T.token env node and raw = T.text env node in
  match node.N.type_ with
  | "boolean" ->
      Some
        (G.Bool (List.mem (String.lowercase_ascii raw) [ "#t"; "#true" ], tok))
  | "string" ->
      Option.map
        (fun value -> G.String (Tok.fake_bracket tok (value, tok)))
        (decode (String.sub raw 1 (String.length raw - 2)))
  | "keyword" -> Some (G.Atom (tok, (raw, tok)))
  | "character" -> Some (G.Char (raw, tok))
  | "number" -> (
      let numeric = String.lowercase_ascii raw in
      let numeric =
        if String.starts_with ~prefix:"#x" numeric then
          "0x" ^ String.sub numeric 2 (String.length numeric - 2)
        else if String.starts_with ~prefix:"#o" numeric then
          "0o" ^ String.sub numeric 2 (String.length numeric - 2)
        else if String.starts_with ~prefix:"#b" numeric then
          "0b" ^ String.sub numeric 2 (String.length numeric - 2)
        else if String.starts_with ~prefix:"#d" numeric then
          String.sub numeric 2 (String.length numeric - 2)
        else numeric
      in
      match Int64.of_string_opt numeric with
      | Some value -> Some (G.Int (Some value, tok))
      | None -> Some (G.Float (float_of_string_opt numeric, tok)))
  | _ -> None

let quoted env node =
  match atom env node with
  | Some value -> G.L value |> G.e
  | None ->
      G.RawExpr (Raw_tree.Case ("Quot_lit", Raw_tree.Token (T.ident env node)))
      |> G.e

let render_symbol name =
  let safe =
    String.length name > 0
    && String.for_all
         (fun char ->
           not
             (List.mem char
                [
                  ' ';
                  '\t';
                  '\r';
                  '\n';
                  '(';
                  ')';
                  '[';
                  ']';
                  '{';
                  '}';
                  '"';
                  '\'';
                  '`';
                  ',';
                  ';';
                  '#';
                  '|';
                  '\\';
                ]))
         name
  in
  if safe then name
  else
    "|"
    ^ String.concat ""
        (List.init (String.length name) (fun i ->
             match name.[i] with
             | '|' -> "\\|"
             | '\\' -> "\\\\"
             | c -> String.make 1 c))
    ^ "|"
