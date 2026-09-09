let direct () =
  (* ruleid: local-flow *)
  sink (source ())
let local () =
  let value = source () in
  (* ruleid: local-flow *)
  sink value
let shadow () =
  let value = source () in
  let value = "fixed" in
  (* ok: local-flow *)
  sink value
