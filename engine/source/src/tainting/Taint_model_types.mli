val lval_of_expression : AST_generic.expr -> IL.lval option

val has_type :
  Metavariable.bindings ->
  string option ->
  string ->
  Shape_and_sig.Shape.shape ->
  bool

val constraint_holds :
  ?report_unresolved:bool ->
  Lang.t ->
  Taint_lval_env.t ->
  Metavariable.bindings ->
  (string * string * string option) option ->
  bool

val establish :
  string ->
  singleton:bool ->
  Shape_and_sig.Shape.shape ->
  Shape_and_sig.Shape.shape

val unresolved : Tok.location -> unit
val reset_diagnostics : unit -> unit
val take_diagnostics : unit -> (string * Tok.location option) list
val from_model : string -> Xtaint.t -> bool
val share_value : Lang.t -> Taint_lval_env.t -> IL.lval -> Taint_lval_env.t
val is_shared_name : IL.name -> bool
val call_limit : IL.orig -> unit
val without_call_limit_diagnostics : (unit -> 'a) -> 'a

val source_shape :
  Rule.taint_source list ->
  Shape_and_sig.Shape.shape ->
  Shape_and_sig.Shape.shape

val immutable_template_write : IL.orig -> unit

val array_shape_limit : IL.orig -> unit
