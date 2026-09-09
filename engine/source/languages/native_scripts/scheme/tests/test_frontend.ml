module G = AST_generic
module T = Native_script_tree

let target source check =
  let file = Filename.temp_file "scheme-native-" ".scm" in
  Fun.protect
    ~finally:(fun () -> Sys.remove file)
    (fun () ->
      let output = open_out_bin file in
      Fun.protect
        ~finally:(fun () -> close_out output)
        (fun () -> output_string output source);
      check (Parse_scheme_native.parse (Fpath.v file)))

let () =
  target
    "#| (sink (source)) #| nested |# |#\n\
     #; (sink (source))\n\
     '(sink (source))\n\
     #((sink (source)))\n" (fun result ->
      if result.T.parsed.errors <> [] || result.diagnostics.semantic_gaps <> []
      then failwith "Scheme reader rejected valid non-executable data";
      let calls = ref 0 in
      let visitor =
        object
          inherit [_] G.iter_no_id_info as super

          method! visit_expr () value =
            (match value.G.e with
            | G.Call _ -> incr calls
            | _ -> ());
            super#visit_expr () value
        end
      in
      Option.iter (visitor#visit_program ()) result.parsed.program;
      if !calls <> 0 then
        failwith "Scheme comments or quoted data became executable calls");
  List.iter
    (fun source ->
      let result = Parse_scheme_native.parse_pattern source in
      if result.errors <> [] then
        failwith ("Valid Scheme pattern rejected: " ^ source))
    [
      "($CALL ...)";
      "(lambda (first . rest) (sink rest))";
      "(lambda rest (sink rest))";
      "(define ($NAME ... ) ...)";
      "(use-modules ((web request) #:select ((request-uri . uri)) #:prefix \
       http:))";
    ];
  List.iter
    (fun source ->
      let result = Parse_scheme_native.parse_pattern source in
      if result.errors = [] then
        failwith ("Invalid or unsupported Scheme pattern accepted: " ^ source))
    [
      "(sink (source)";
      "(lambda (first . rest extra) (sink first))";
      "(define-syntax ignored (syntax-rules () ((_ body) #t)))";
    ]

let () =
  let prefix = "; café\r\n" in
  target (prefix ^ "(sink (source)\n") (fun result ->
      if result.T.parsed.errors = [] then
        failwith "Missing Scheme delimiter lost its diagnostic";
      List.iter
        (fun location ->
          if
            location.Tok.pos.line <> 2
            || location.pos.bytepos
               <> String.length prefix + location.pos.column
          then failwith "Scheme syntax diagnostic lost its UTF-8 byte position")
        (result.diagnostics.inserted_tokens @ result.diagnostics.skipped_tokens))

let () =
  target "#!fold-case\n(define (SYSTEM input) input)\n(system (source))\n"
    (fun result ->
      if result.T.diagnostics.semantic_gaps = [] then
        failwith "Unsupported reader mode was silently ignored";
      let calls = ref 0 in
      let visitor =
        object
          inherit [_] G.iter_no_id_info as super

          method! visit_expr () value =
            (match value.G.e with
            | G.Call _ -> incr calls
            | _ -> ());
            super#visit_expr () value
        end
      in
      Option.iter (visitor#visit_program ()) result.parsed.program;
      if !calls <> 0 then
        failwith "Unsupported reader mode produced executable claims")
