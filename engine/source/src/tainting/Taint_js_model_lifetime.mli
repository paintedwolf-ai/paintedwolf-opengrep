val invalidate : Taint_lval_env.t -> IL.lval -> Taint_lval_env.t

val instruction :
  preserved:Range.t list ->
  lambdas:IL.lambdas_cfgs ->
  Taint_lval_env.t ->
  IL.instr ->
  Taint_lval_env.t
(** Calls that may mutate an instance invalidate its unproven member identities.
*)
