type t = { minimum : int; maximum : int option }

let unknown = { minimum = 0; maximum = None }
let exact length = { minimum = length; maximum = Some length }
let unknown_upper length = { length with maximum = None }
let equal left right =
  Int.equal left.minimum right.minimum
  && Option.equal Int.equal left.maximum right.maximum
let compare left right =
  let lower = Int.compare left.minimum right.minimum in
  if Int.equal lower 0 then Option.compare Int.compare left.maximum right.maximum else lower
let join left right =
  { minimum = min left.minimum right.minimum;
    maximum = if Option.equal Int.equal left.maximum right.maximum then left.maximum else None }
let add length count =
  let safe_add left right = if left > max_int - right then max_int else left + right in
  { minimum = safe_add length.minimum count;
    maximum = Option.bind length.maximum (fun prior ->
      if prior > max_int - count then None else Some (prior + count)) }
let concat left right =
  let combined = add left right.minimum in
  { combined with maximum =
      match left.maximum, right.maximum with
      | Some a, Some b when a <= max_int - b -> Some (a + b)
      | _ -> None }

let exact_value length =
  match length.maximum with
  | Some upper when Int.equal upper length.minimum -> Some upper
  | _ -> None
let index_write length index =
  if index < 0 || index >= 4_294_967_295 then length
  else {minimum = max length.minimum (index + 1);
    maximum = Option.map (fun upper -> max upper (index + 1)) length.maximum}
let show length =
  Printf.sprintf "%d..%s" length.minimum
    (Option.fold ~none:"?" ~some:string_of_int length.maximum)
