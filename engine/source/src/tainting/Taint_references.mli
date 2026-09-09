val assignment :
  before:Taint_lval_env.t ->
  Lang.t ->
  Taint_lval_env.t ->
  IL.lval ->
  IL.exp ->
  Taint_lval_env.t
(** Reference identities retained inside newly constructed containers. *)
