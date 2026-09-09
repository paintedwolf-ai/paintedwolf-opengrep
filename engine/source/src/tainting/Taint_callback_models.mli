type origin =
  | Propagation of Dataflow_var_env.var
  | Source of Taint.Taint_set.t * Shape_and_sig.Shape.shape

type request = {
  closures : IL.NameSet.t;
  limitation : string option;
  value_range : Range.t;
  parameter : Rule.callback_parameter;
  origin : origin;
  location : Tok.location;
}

type input =
  IL.name
  * Rule.callback_parameter
  * Taint.Taint_set.t
  * Shape_and_sig.Shape.shape
  * Tok.location

val targets :
  Rule.callback_parameter ->
  Shape_and_sig.Shape.shape ->
  IL.NameSet.t * string option

val preserved_arrays : Taint_lval_env.t -> request list -> Range.t list

val resolve :
  Taint_lval_env.t ->
  IL.lambdas_cfgs ->
  request list ->
  input list * Taint_lval_env.t

val seed :
  Lang.t ->
  IL.name ->
  IL.param list ->
  input list ->
  Taint_lval_env.t ->
  Taint_lval_env.t list

val reset_diagnostics : unit -> unit
val take_diagnostics : unit -> (string * Tok.location option) list
