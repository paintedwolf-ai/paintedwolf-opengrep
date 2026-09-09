type t
type path = IL.name * Taint.offset list

val empty : t
val equal : t -> t -> bool
val is_limited : t -> bool
val related : certain:bool -> t -> path -> path list * t
val forget : t -> path -> t
val assignment : t -> target:path -> source:path option -> t * t
val join : t -> t -> t
val filter : (IL.name -> bool) -> t -> t
val reset_diagnostics : unit -> unit
val take_diagnostics : unit -> Tok.location option list
val to_string : t -> string
val equal_path : path -> path -> bool

val copy_reference :
  before:t -> replaced:path -> t -> target:path -> source:path -> t

type array_change = Prepend of Sequence_length.t | Resize of int option
val reindex_array : t -> target:path -> array_change -> t
val copy_array_element : before:t -> array:path -> change:array_change option ->
  t -> target:path -> source:path -> t
