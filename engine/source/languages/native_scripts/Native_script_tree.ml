module G = AST_generic
module N = Tree_sitter_bindings.Tree_sitter_output_t
module R = Tree_sitter_run
module H = Parse_tree_sitter_helpers

type node = N.node
type diagnostics = {
  skipped_tokens: Tok.location list;
  inserted_tokens: Tok.location list;
  semantic_gaps: (string * Tok.location) list;
}
type result = {
  parsed: (G.program, unit) R.Parsing_result.t;
  diagnostics: diagnostics;
}
type env = { src: R.Src_file.t; locations: unit H.env; pattern: bool; errors: R.Tree_sitter_error.t list ref; skipped_tokens: Tok.location list ref; inserted_tokens: Tok.location list ref; semantic_gaps: (string * Tok.location) list ref }

let children node = Option.value ~default:[] node.N.children
let named node = children node |> List.filter (fun node -> match node.N.kind with N.Name _ | N.Error -> true | _ -> false)
let text env node = R.Src_file.get_region env.src node.N.start_pos node.N.end_pos
let token env node = H.token env.locations (R.Loc.{start=node.N.start_pos; end_=node.N.end_pos}, text env node)
let ident env node = text env node, token env node
let name env node = G.N (G.Id (ident env node, G.empty_id_info ())) |> G.e
let punctuation env node value =
  match List.find_opt (fun child -> text env child = value) (children node) with
  | Some child -> token env child
  | None -> Tok.fake_tok (token env node) value
let bracket env node contents =
  let parts = children node in
  match parts, List.rev parts with
  | first :: _, last :: _ when List.mem (text env first, text env last)
      [("(", ")"); ("[", "]"); ("{", "}")] ->
      token env first, contents, token env last
  | _ -> Tok.fake_bracket (token env node) contents
let call env node fn args = G.Call (fn, bracket env node (List.map (fun expr -> G.Arg expr) args)) |> G.e
let dot env node receiver field = G.DotAccess (receiver, punctuation env node ".", G.FN (G.Id (ident env field, G.empty_id_info ()))) |> G.e
let literal env node value = G.L (G.String (Tok.fake_bracket (token env node) (value, token env node))) |> G.e
let comment node = List.mem node.N.type_ ["comment"; "line_comment"; "block_comment"; "pod"; "shebang"; "groovy_doc"]
let code_children node = named node |> List.filter (fun node -> not (comment node))

let unsupported env node =
  if env.pattern then (
    let error = R.Tree_sitter_error.create Error_node env.src node ("Unsupported " ^ node.N.type_ ^ " pattern") in
    env.errors := error :: !(env.errors))
  else if node.N.kind <> N.Error && not node.N.is_missing then (
    let gap = (node.N.type_, Tok.unsafe_loc_of_tok (token env node)) in
    if not (List.mem gap !(env.semantic_gaps)) then
      env.semantic_gaps := gap :: !(env.semantic_gaps));
  G.OtherExpr ((node.N.type_, token env node), []) |> G.e

let assignment env node left right = G.Assign (left, punctuation env node "=", right) |> G.e
let declaration env _node identifier value =
  G.DefStmt (G.basic_entity (ident env identifier), G.VarDef {G.vinit=Some value; vtype=None; vtok=G.no_sc}) |> G.s
let block env node statements = G.Block (bracket env node statements) |> G.s
let function_definition env node identifier parameters body =
  G.DefStmt (G.basic_entity (ident env identifier), G.FuncDef {
    G.fkind=(G.Function, token env node); fparams=bracket env node parameters;
    frettype=None; fbody=G.FBStmt body }) |> G.s
let parameter env node = G.Param (G.param_of_id (ident env node))
let concat env node parts = call env node (G.IdSpecial (G.ConcatString G.InterpolatedConcat, token env node) |> G.e) parts

let environment ~pattern parsed =
  let src = parsed.R.Tree_sitter_parsing.src in
  let offsets = Array.make (Array.length src.R.Src_file.lines + 1) 0 in
  Array.iteri (fun i line -> offsets.(i+1) <- offsets.(i) + String.length line) src.lines;
  let conv (line, column) = offsets.(line-1) + column in
  {src; pattern; errors=ref []; skipped_tokens=ref []; inserted_tokens=ref []; semantic_gaps=ref []; locations={H.file=Fpath.v src.info.name; conv; extra=()}}

let parse_tree ~pattern map parsed =
  let env = environment ~pattern parsed in
  let rec syntax node =
    if node.N.kind = N.Error || node.N.is_missing then (
      let kind : R.Tree_sitter_error_t.error_kind = if node.N.is_missing && not env.pattern then Missing_node else Error_node in
      let error = R.Tree_sitter_error.create kind env.src node "Invalid syntax" in
      env.errors := error :: !(env.errors);
      let location = Tok.unsafe_loc_of_tok (token env node) in
      let locations = if node.N.is_missing then env.inserted_tokens else env.skipped_tokens in
      locations := location :: !locations);
    List.iter syntax (children node) in
  syntax parsed.R.Tree_sitter_parsing.root;
  let program = map env parsed.root in
  { parsed=R.Parsing_result.create env.src (Some program) [] (List.rev !(env.errors));
    diagnostics={ skipped_tokens=List.rev !(env.skipped_tokens);
      inserted_tokens=List.rev !(env.inserted_tokens);
      semantic_gaps=List.rev !(env.semantic_gaps) } }

let file parser map path =
  let parsed = R.Tree_sitter_parsing.parse_source_file (Domain.DLS.get parser) (Fpath.to_string path) in
  parse_tree ~pattern:false map parsed
let pattern parser map source =
  let parsed = R.Tree_sitter_parsing.parse_source_string ~src_file:"<pattern>" (Domain.DLS.get parser) source in
  let {parsed=result; _} = parse_tree ~pattern:true map parsed in
  {result with R.Parsing_result.program = Option.map (fun statements -> G.Pr statements) result.program}

let operator env node =
  let tokens = children node |> List.filter (fun n -> match n.N.kind with N.Literal _ -> true | _ -> false) in
  match tokens with
  | [op] -> (match String.lowercase_ascii (text env op) with
    | "+" | "." -> Some G.Plus | "-" -> Some G.Minus | "*" -> Some G.Mult
    | "==" | "eq" | "-eq" -> Some G.Eq | "!=" | "ne" | "-ne" -> Some G.NotEq
    | "&&" | "and" | "-and" -> Some G.And | "||" | "or" | "-or" -> Some G.Or
    | "<" | "-lt" -> Some G.Lt | ">" | "-gt" -> Some G.Gt
    | _ -> None)
  | _ -> None
