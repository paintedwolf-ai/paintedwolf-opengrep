let () =
  let check text (line, column, offset) (end_line, end_column, end_offset) =
    let location : Tok.location =
      {str=text; pos={file=Fpath.v "source"; line; column; bytepos=offset}} in
    let start, end_ = Semgrep_output_utils.position_range location location in
    if start.line <> line || start.col <> column + 1 || start.offset <> offset then
      failwith "Output changed a token's start position";
    if end_.line <> end_line || end_.col <> end_column + 1 || end_.offset <> end_offset then
      failwith "Output endpoint does not identify the original byte boundary"
  in
  check "" (1, 0, 0) (1, 0, 0);
  check "value" (3, 4, 20) (3, 9, 25);
  check "value\n" (3, 4, 20) (4, 0, 26);
  check "value\r\n" (3, 4, 20) (4, 0, 27);
  check "é\r\n" (3, 4, 20) (4, 0, 24);
  check "a\n\n" (3, 4, 20) (5, 0, 23);
  check "a\nb" (3, 4, 20) (4, 1, 23)
