let () =
  let valid = Parse_powershell_native.parse_pattern "Read-Input" in
  (match valid.program, valid.errors with
  | Some (AST_generic.Pr (_ :: _)), [] -> ()
  | _ -> failwith "Native parser rejected an ordinary command");
  let malformed = Parse_powershell_native.parse_pattern "(" in
  if List.is_empty malformed.errors then
    failwith "Native parser accepted an unmatched delimiter"


let () =
  let prefix = "# café\n" in
  let unsupported = "try { 'safe' } catch { 'safe' }" in
  let filename = Filename.temp_file "native-diagnostic-" ".source" in
  Fun.protect ~finally:(fun () -> Sys.remove filename) (fun () ->
    let channel = open_out_bin filename in
    Fun.protect ~finally:(fun () -> close_out channel) (fun () ->
      output_string channel (prefix ^ unsupported ^ "\n"));
    let {Native_script_tree.parsed; diagnostics} = Parse_powershell_native.parse (Fpath.v filename) in
    let gaps = diagnostics.semantic_gaps in
    if not (List.is_empty parsed.errors) then
      failwith "Unsupported valid syntax was classified as malformed";
    match gaps with
    | [(_, location)] when location.Tok.pos.line = 2
        && location.pos.column = 0
        && location.pos.bytepos = String.length prefix -> ()
    | _ -> failwith "Semantic limitation lost its original byte location");
  let pattern = Parse_powershell_native.parse_pattern unsupported in
  if List.is_empty pattern.errors then
    failwith "Unsupported pattern was accepted as a valid rule"

let () =
  let prefix = "# café\r\n" in
  let filename = Filename.temp_file "native-syntax-" ".source" in
  Fun.protect ~finally:(fun () -> Sys.remove filename) (fun () ->
    let channel = open_out_bin filename in
    Fun.protect ~finally:(fun () -> close_out channel) (fun () ->
      output_string channel (prefix ^ "Write-Output 'safe' )"));
    let {Native_script_tree.parsed; diagnostics} = Parse_powershell_native.parse (Fpath.v filename) in
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
  let result = Parse_powershell_native.parse_pattern "if ($true) { Write-Output 'safe'" in
  if not (List.exists (fun (error : Tree_sitter_run.Tree_sitter_error.t) ->
    match error.kind with Error_node -> true | _ -> false) result.errors) then
    failwith "Incomplete native pattern was accepted by the pattern-error boundary"

let () =
  let prefix = "# café\r\n" in
  let source = "function f { Read-Input" in
  let filename = Filename.temp_file "native-inserted-" ".source" in
  Fun.protect ~finally:(fun () -> Sys.remove filename) (fun () ->
    let channel = open_out_bin filename in
    Fun.protect ~finally:(fun () -> close_out channel) (fun () ->
      output_string channel (prefix ^ source ^ "\n"));
    let {Native_script_tree.parsed; diagnostics} = Parse_powershell_native.parse (Fpath.v filename) in
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
  let pattern = Parse_powershell_native.parse_pattern source in
  if not (List.exists (fun (error : Tree_sitter_run.Tree_sitter_error.t) ->
    match error.kind with Error_node -> true | _ -> false) pattern.errors) then
    failwith "Inserted delimiter made an incomplete rule acceptable"
