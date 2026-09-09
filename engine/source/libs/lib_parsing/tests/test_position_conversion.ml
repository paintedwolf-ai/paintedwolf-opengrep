let () =
  List.iter (fun source ->
    let name = Filename.temp_file "opengrep-position-" ".txt" in
    Fun.protect ~finally:(fun () -> Sys.remove name) (fun () ->
      let channel = open_out_bin name in
      output_string channel source;
      close_out channel;
      let file = Pos.full_converters_large (Fpath.v name) in
      let text = Pos.full_converters_str source in
      for offset = 0 to String.length source do
        let expected = text.bytepos_to_linecol_fun offset in
        let actual = file.bytepos_to_linecol_fun offset in
        if actual <> expected then
          failwith (Printf.sprintf "File/string position mismatch at %d of %S" offset source);
        if file.linecol_to_bytepos_fun expected <> offset then
          failwith (Printf.sprintf "File position does not round-trip at %d of %S" offset source)
      done))
    [""; "a"; "\n"; "a\n"; "a\r\n"; "é\r\n"; "a\n\n"; "a\nb"; "\n    line1\n    line2\n"]
