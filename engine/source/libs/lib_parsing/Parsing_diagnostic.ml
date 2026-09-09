type t =
  | Syntax of Tok.location
  | Unsupported_semantics of string * Tok.location

let map_location f = function
  | Syntax location -> Syntax (f location)
  | Unsupported_semantics (construct, location) ->
      Unsupported_semantics (construct, f location)
