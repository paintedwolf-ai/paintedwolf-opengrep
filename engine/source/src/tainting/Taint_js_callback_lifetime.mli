val instruction :
  preserved:Range.t list -> Taint_lval_env.t -> IL.instr -> Taint_lval_env.t
(** Unmodeled calls and length writes invalidate stored callback identities. *)
