module G = AST_generic
module T = Taint
module Taints = T.Taint_set
module S = Shape_and_sig.Shape
module Fields = Shape_and_sig.Fields
module Shape = Taint_shape

type bound = Default | Integer of int | Unknown

let bound eval expression =
  match eval expression with
  | G.Lit (G.Null _) -> Default
  | G.Lit (G.Int value) ->
      Option.fold ~none:Unknown
        ~some:(fun value -> Integer value)
        (Parsed_int.to_int_opt value)
  | _ -> Unknown

let sequence_length = function
  | S.Array value -> Sequence_length.exact_value value.length
  | S.Obj fields ->
      let count, maximum, valid =
        Fields.fold
          (fun offset _ (count, maximum, valid) ->
            match offset with
            | T.Oint index when index >= 0 ->
                (count + 1, max maximum index, valid)
            | _ -> (count, maximum, false))
          fields (0, -1, true)
      in
      if valid && Int.equal count (maximum + 1) then Some count else None
  | _ -> None

let selected_indices length start stop step =
  let step =
    match step with
    | Default -> Some 1
    | Integer n when not (Int.equal n 0) -> Some n
    | _ -> None
  in
  let normalize ~default ~low ~high = function
    | Default -> Some default
    | Integer n -> Some (max low (min high (if n < 0 then n + length else n)))
    | Unknown -> None
  in
  let ( let* ) = Option.bind in
  let* step = step in
  let* start =
    if step > 0 then normalize ~default:0 ~low:0 ~high:length start
    else normalize ~default:(length - 1) ~low:(-1) ~high:(length - 1) start
  in
  let* stop =
    if step > 0 then normalize ~default:length ~low:0 ~high:length stop
    else normalize ~default:(-1) ~low:(-1) ~high:(length - 1) stop
  in
  let rec collect index acc =
    if
      (step > 0 && index >= Int64.of_int stop)
      || (step < 0 && index <= Int64.of_int stop)
    then List.rev acc
    else
      collect (Int64.add index (Int64.of_int step)) (Int64.to_int index :: acc)
  in
  Some (collect (Int64.of_int start) [])

let slice ~eval ~taints ~shape start stop step =
  let selected =
    Option.bind (sequence_length shape) (fun length ->
        selected_indices length (bound eval start) (bound eval stop)
          (bound eval step))
  in
  match selected with
  | Some [] -> (Taints.empty, S.Bot)
  | Some indices ->
      let values =
        List.map
          (fun index ->
            Option.value ~default:(taints, S.Bot)
              (Shape.find_in_shape_poly ~taints [ T.Oint index ] shape))
          indices
      in
      (Taints.empty, Shape.tuple_like_obj values)
  | None -> (Taints.union taints (Shape.gather_all_taints_in_shape shape), S.Bot)
