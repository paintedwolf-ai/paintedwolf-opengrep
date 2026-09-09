let () =
  let valid = Parse_perl_native.parse_pattern "source();" in
  (match valid.program, valid.errors with
  | Some (AST_generic.Pr (_ :: _)), [] -> ()
  | _ -> failwith "Native parser rejected an ordinary command");
  let malformed = Parse_perl_native.parse_pattern "(" in
  if List.is_empty malformed.errors then
    failwith "Native parser accepted an unmatched delimiter"

let () =
  List.iter (fun source ->
    let parsed = Parse_perl_native.parse_pattern source in
    if not (List.is_empty parsed.errors) then
      failwith ("Perl pattern ellipsis rejected: " ^ source))
    ["..."; "sink(...)"; "sink($VALUE, ...)"; "sub handler { ... }" ];
  let check source valid =
    let filename = Filename.temp_file "native-perl-placeholder-" ".pl" in
    Fun.protect ~finally:(fun () -> Sys.remove filename) (fun () ->
      let channel = open_out_bin filename in
      Fun.protect ~finally:(fun () -> close_out channel) (fun () -> output_string channel source);
      let {Native_script_tree.parsed; diagnostics} = Parse_perl_native.parse (Fpath.v filename) in
      if List.is_empty parsed.errors <> valid then
        failwith ("Perl placeholder syntax classification: " ^ source);
      if valid then (
        if not (List.exists (fun (kind, _) -> kind = "yadayada") diagnostics.semantic_gaps) then
          failwith "Perl placeholder statement lost its semantic limit")
      else match diagnostics.skipped_tokens with
        | [location] when location.Tok.str = "..." && location.pos.bytepos = 5 -> ()
        | _ -> failwith "Perl pattern-only expression lost its source error location")
  in
  check "...;" true;
  check "sink(...);" false


let () =
  let prefix = "# café\n" in
  let unsupported = "local $value;" in
  let filename = Filename.temp_file "native-diagnostic-" ".source" in
  Fun.protect ~finally:(fun () -> Sys.remove filename) (fun () ->
    let channel = open_out_bin filename in
    Fun.protect ~finally:(fun () -> close_out channel) (fun () ->
      output_string channel (prefix ^ unsupported ^ "\n"));
    let {Native_script_tree.parsed; diagnostics} = Parse_perl_native.parse (Fpath.v filename) in
    let gaps = diagnostics.semantic_gaps in
    if not (List.is_empty parsed.errors) then
      failwith "Unsupported valid syntax was classified as malformed";
    match gaps with
    | [(_, location)] when location.Tok.pos.line = 2
        && location.pos.column = 0
        && location.pos.bytepos = String.length prefix -> ()
    | _ -> failwith "Semantic limitation lost its original byte location");
  let pattern = Parse_perl_native.parse_pattern unsupported in
  if List.is_empty pattern.errors then
    failwith "Unsupported pattern was accepted as a valid rule"

let () =
  let prefix = "# café\r\n" in
  let filename = Filename.temp_file "native-syntax-" ".source" in
  Fun.protect ~finally:(fun () -> Sys.remove filename) (fun () ->
    let channel = open_out_bin filename in
    Fun.protect ~finally:(fun () -> close_out channel) (fun () ->
      output_string channel (prefix ^ "sink($value));"));
    let {Native_script_tree.parsed; diagnostics} = Parse_perl_native.parse (Fpath.v filename) in
    let locations = diagnostics.skipped_tokens @ diagnostics.inserted_tokens in
    if List.is_empty parsed.errors || List.length locations <> List.length parsed.errors then
      failwith "Native syntax recovery lost a diagnostic";
    List.iter (fun location ->
      if location.Tok.pos.line <> 2
         || location.pos.bytepos <> String.length prefix + location.pos.column then
        failwith (Printf.sprintf "Native syntax offset: line=%d column=%d byte=%d prefix=%d" location.pos.line location.pos.column location.pos.bytepos (String.length prefix))) locations;
    Printf.printf "Native syntax locations: %d skipped, %d inserted\n"
      (List.length diagnostics.skipped_tokens) (List.length diagnostics.inserted_tokens))

let () =
  let result = Parse_perl_native.parse_pattern "if ($value) { sink($value);" in
  if not (List.exists (fun (error : Tree_sitter_run.Tree_sitter_error.t) ->
    match error.kind with Error_node -> true | _ -> false) result.errors) then
    failwith "Incomplete native pattern was accepted by the pattern-error boundary"

let () =
  let prefix = "# café\r\n" in
  let source = "my $x = (source();" in
  let filename = Filename.temp_file "native-inserted-" ".source" in
  Fun.protect ~finally:(fun () -> Sys.remove filename) (fun () ->
    let channel = open_out_bin filename in
    Fun.protect ~finally:(fun () -> close_out channel) (fun () ->
      output_string channel (prefix ^ source ^ "\n"));
    let {Native_script_tree.parsed; diagnostics} = Parse_perl_native.parse (Fpath.v filename) in
    if not (List.is_empty diagnostics.skipped_tokens) then
      failwith "Missing delimiter was replaced by an error-node diagnostic";
    (match diagnostics.inserted_tokens with
    | [location] when location.Tok.pos.line = 2
        && location.pos.bytepos = String.length prefix + location.pos.column
        && String.length location.str = 0 -> ()
    | _ -> failwith "Inserted delimiter lost its zero-width byte location");
    if not (List.exists (fun (error : Tree_sitter_run.Tree_sitter_error.t) ->
      match error.kind with Missing_node -> true | _ -> false) parsed.errors) then
      failwith "Missing delimiter was not retained in target diagnostics");
  let pattern = Parse_perl_native.parse_pattern source in
  if not (List.exists (fun (error : Tree_sitter_run.Tree_sitter_error.t) ->
    match error.kind with Error_node -> true | _ -> false) pattern.errors) then
    failwith "Inserted delimiter made an incomplete rule acceptable"

let () =
  let module G = AST_generic in
  List.iter (fun (source, expected) ->
    let result = Parse_perl_native.parse_pattern source in
    match result.program, result.errors with
    | Some (G.Pr [{s = G.ExprStmt ({e = G.AssignOp (_, (op, _), _); _}, _); _}]), []
      when op = expected -> ()
    | _ -> failwith ("Perl compound assignment lost its operator: " ^ source))
    ["$VALUE .= $MORE", G.Concat; "$VALUE += $MORE", G.Plus;
     "$VALUE &&= $MORE", G.And; "$VALUE ||= $MORE", G.Or;
     "$VALUE //= $MORE", G.Nullish];
  List.iter (fun source ->
    let result = Parse_perl_native.parse_pattern source in
    if not (List.is_empty result.errors) then
      failwith ("Perl short-circuit pattern rejected: " ^ source))
    ["$LEFT && $RIGHT"; "$LEFT || $RIGHT"; "$LEFT // $RIGHT";
     "$LEFT and $RIGHT"; "$LEFT or $RIGHT"; "not $VALUE"; "!$VALUE"]

let () =
  let module G = AST_generic in
  let result = Parse_perl_native.parse_pattern "my ($FIRST, $SECOND) = (source(), 'fixed');" in
  (match result.program, result.errors with
   | Some (G.Pr [{s = G.DefStmt ({name = G.EPattern (G.PatTuple (_, patterns, _)); _}, G.VarDef _); _}]), [] ->
       let names = List.filter_map (function G.PatId ((name, _), _) -> Some name | _ -> None) patterns in
       if names <> ["$FIRST"; "$SECOND"] then
         failwith "Perl lexical list lost its distinct bindings"
   | _ -> failwith "Perl lexical list did not produce a binding pattern");
  List.iter (fun source ->
    let parsed = Parse_perl_native.parse_pattern source in
    if List.is_empty parsed.errors then
      failwith ("Perl dynamic or persistent declaration was treated as a lexical binding: " ^ source))
    ["our $VALUE = source();"; "state $VALUE = source();"]
