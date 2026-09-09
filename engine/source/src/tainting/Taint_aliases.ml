module Path = struct
  type t = IL.name * Taint.offset list

  let compare (left, left_fields) (right, right_fields) =
    match IL.compare_name left right with
    | 0 -> List.compare Shape_and_sig.Field.compare left_fields right_fields
    | result -> result
end

module Paths = Set.Make (Path)

module Edge_set = Set.Make (struct
  type t = Path.t * Path.t

  let compare (a, b) (c, d) =
    match Path.compare a c with
    | 0 -> Path.compare b d
    | result -> result
end)

module Edges = struct
  type t = { all : Edge_set.t; by_root : Edge_set.t IL.NameMap.t }

  let empty = { all = Edge_set.empty; by_root = IL.NameMap.empty }
  let equal left right = Edge_set.equal left.all right.all
  let cardinal edges = Edge_set.cardinal edges.all
  let mem edge edges = Edge_set.mem edge edges.all
  let fold visit edges initial = Edge_set.fold visit edges.all initial
  let elements edges = Edge_set.elements edges.all

  let add (((left, _), (right, _)) as edge) edges =
    if mem edge edges then edges
    else
      let index root entries =
        IL.NameMap.update root
          (fun previous ->
            Some
              (Edge_set.add edge
                 (Option.value previous ~default:Edge_set.empty)))
          entries
      in
      {
        all = Edge_set.add edge edges.all;
        by_root = index right (index left edges.by_root);
      }

  let of_set all = Edge_set.fold add all empty
  let filter keep edges = of_set (Edge_set.filter keep edges.all)
  let inter left right = of_set (Edge_set.inter left.all right.all)

  let at_root root edges = Option.value ~default:Edge_set.empty (IL.NameMap.find_opt root edges.by_root)

  let iter_root root visit edges =
    Option.iter (Edge_set.iter visit) (IL.NameMap.find_opt root edges.by_root)
end

type path = Path.t

let equal_path left right = Path.compare left right = 0

type t = { must : Edges.t; may : Edges.t; limited : bool }

let empty = { must = Edges.empty; may = Edges.empty; limited = false }
let max_paths = 128
let max_depth = 16
let max_edges = 1024
let max_rewrites = 1_000_000
let rewrites = Domain.DLS.new_key (fun () -> ref max_rewrites)

module Rewrite_cache = Hashtbl.Make (struct
  type t = bool * bool * Edge_set.t * path
  let equal (slot, possible, edges, path) (other_slot, other_possible, other_edges, other_path) =
    Bool.equal slot other_slot && Bool.equal possible other_possible
    && Path.compare path other_path = 0 && Edge_set.equal edges other_edges
  let hash (slot, possible, edges, (name, offsets)) =
    Hashtbl.hash (slot, possible, Edge_set.cardinal edges, IL.str_of_name name, List.length offsets)
end)

let rewrite_cache = Domain.DLS.new_key (fun () -> Rewrite_cache.create max_edges)

let diagnostic : Tok.location option option ref Domain.DLS.key =
  Domain.DLS.new_key (fun () -> ref None)

let reset_diagnostics () =
  Domain.DLS.get diagnostic := None;
  Domain.DLS.get rewrites := max_rewrites;
  Rewrite_cache.clear (Domain.DLS.get rewrite_cache)

let take_diagnostics () =
  let current = Domain.DLS.get diagnostic in
  let result =
    match !current with
    | None -> []
    | Some location -> [ location ]
  in
  current := None;
  result

let path_location (name, _) =
  match Tok.loc_of_tok (snd name.IL.ident) with
  | Ok location -> Some location
  | Error _ ->
      Option.bind name.IL.value_origin (fun origin ->
          Option.map fst
            (AST_generic_helpers.range_of_any_opt (AST_generic.E origin)))

let record_limit path =
  let current = Domain.DLS.get diagnostic in
  match (!current, path_location path) with
  | None, location -> current := Some location
  | Some None, Some location -> current := Some (Some location)
  | Some _, _ -> ()

let equal left right =
  Edges.equal left.must right.must
  && Edges.equal left.may right.may
  && Bool.equal left.limited right.limited

let is_limited state = state.limited

let suffix ?(possible = false) (base, prefix) (other, fields) =
  let rec strip prefix fields =
    match (prefix, fields) with
    | [], suffix -> Some suffix
    | left :: prefix, right :: fields
      when Shape_and_sig.Field.compare left right = 0
           || (possible && (match left, right with
             | Taint.Oany, _ | _, Taint.Oany -> true
             | Taint.Oslice first, Taint.Oint index | Taint.Oint index, Taint.Oslice first -> index >= first
             | Taint.Oslice _, Taint.Oslice _ -> true
             | _ -> false)) ->
        strip prefix fields
    | _ -> None
  in
  if IL.compare_name base other <> 0 then None else strip prefix fields

let is_within prefix path = Option.is_some (suffix prefix path)

let substitute ~slot ~possible source (base, fields) path =
  match suffix ~possible source path with
  | Some [] when slot -> None
  | rest -> Option.map (fun rest -> (base, fields @ rest)) rest

let add_path limited path paths =
  if Paths.mem path paths then paths
  else if
    List.length (snd path) > max_depth || Paths.cardinal paths >= max_paths
  then (
    limited := true;
    record_limit path;
    paths)
  else Paths.add path paths

let add_edge limited left right edges =
  let order = Path.compare left right in
  if order = 0 then edges
  else
    let edge = if order < 0 then (left, right) else (right, left) in
    if Edges.mem edge edges then edges
    else if Edges.cardinal edges >= max_edges then (
      limited := true;
      record_limit left;
      edges)
    else Edges.add edge edges

let rewrite ?(slot = false) ?(possible = false) limited edges path visit =
  let adjacent = Edges.at_root (fst path) edges in
  let key = (slot, possible, adjacent, path) in
  let cache = Domain.DLS.get rewrite_cache in
  match Rewrite_cache.find_opt cache key with
  | Some values -> List.iter visit values
  | None ->
      let remaining = Domain.DLS.get rewrites in
      let values = ref [] and count = ref 0 in
      let yield value =
        visit value;
        incr count;
        if !count <= max_paths then values := value :: !values in
      let exception Exhausted in
      (try
        Edge_set.iter
          (fun (left, right) ->
            if !remaining <= 0 then (
              limited := true;
              record_limit path;
              raise Exhausted);
            decr remaining;
            Option.iter yield (substitute ~slot ~possible left right path);
            Option.iter yield (substitute ~slot ~possible right left path))
          adjacent;
        if !count <= max_paths then (
          if Rewrite_cache.length cache >= max_edges then Rewrite_cache.clear cache;
          Rewrite_cache.add cache key (List.rev !values))
      with Exhausted -> ())

let must_paths ?(slot = false) limited edges path =
  let visited = ref (Paths.singleton path) in
  let pending = ref [ path ] in
  while (not (List.is_empty !pending)) && !(Domain.DLS.get rewrites) > 0 do
    match !pending with
    | [] -> ()
    | path :: rest ->
        pending := rest;
        rewrite ~slot limited edges path (fun next ->
            let updated = add_path limited next !visited in
            if not (Paths.equal updated !visited) then (
              visited := updated;
              pending := next :: !pending))
  done;
  if not (List.is_empty !pending) then (
    limited := true;
    record_limit path);
  !visited

let may_paths ?(slot = false) limited state path =
  let initial = must_paths ~slot limited state.must path in
  let candidates = ref initial in
  (* May-alias is not transitive across mutually exclusive branches. *)
  Paths.iter
    (fun point ->
      rewrite ~slot ~possible:true limited state.may point (fun next ->
          candidates := add_path limited next !candidates))
    initial;
  Paths.fold
    (fun candidate result ->
      if Paths.mem candidate result then result
      else
        Paths.fold (add_path limited)
          (must_paths ~slot limited state.must candidate)
          result)
    !candidates initial

let related ~certain state path =
  let limited = ref state.limited in
  let paths =
    if certain then must_paths limited state.must path
    else may_paths limited state path
  in
  (Paths.elements paths, { state with limited = !limited })

let close state =
  if state.limited then state
  else
    let limited = ref false in
    let endpoints =
      Edges.fold
        (fun (left, right) paths ->
          paths |> Paths.add left |> Paths.add right)
        state.may Paths.empty
    in
    let must = ref state.must and may = ref state.may in
    Paths.iter
      (fun path ->
        if not !limited then (
          Paths.iter
            (fun other ->
              if not !limited then must := add_edge limited path other !must)
            (must_paths limited state.must path);
          if not !limited then
            Paths.iter
              (fun other ->
                if not !limited then may := add_edge limited path other !may)
              (may_paths limited state path)))
      endpoints;
    { must = !must; may = !may; limited = !limited }

(* Rebinding a slot changes aliases of its container, not references to its old value. *)
let overlaps (base, prefix) (other, fields) =
  let rec strip prefix fields =
    match (prefix, fields) with
    | [], _ -> true
    | left :: prefix, right :: fields
      when (match left, right with
           | Taint.Oany, _ | _, Taint.Oany -> true
           | Taint.Oslice first, Taint.Oint index | Taint.Oint index, Taint.Oslice first -> index >= first
           | Taint.Oslice _, Taint.Oslice _ -> true
           | _ -> Shape_and_sig.Field.compare left right = 0) ->
        strip prefix fields
    | _ -> false
  in
  IL.compare_name base other = 0 && strip prefix fields

let exact_path (_, offsets) =
  not (List.exists (function Taint.Oany | Taint.Oslice _ -> true | _ -> false) offsets)

let assignment state ~target ~source =
  let state = close state in
  let limited = ref state.limited in
  let exact = exact_path target in
  let definite =
    if exact then must_paths ~slot:true limited state.must target
    else Paths.empty
  in
  let possible = may_paths ~slot:true limited state target in
  let affected slots predicate (left, right) =
    Paths.exists (fun slot -> predicate slot left || predicate slot right) slots
  in
  let possible_edge = affected possible overlaps in
  let definite_edge = affected definite is_within in
  let writing =
    {
      must = Edges.filter (fun e -> not (possible_edge e)) state.must;
      may = Edges.filter (fun e -> not (possible_edge e)) state.may;
      limited = !limited;
    }
  in
  let after =
    {
      writing with
      may = Edges.filter (fun e -> not (definite_edge e)) state.may;
    }
  in
  let after =
    match source with
    | None -> after
    | Some source ->
        let certain_sources =
          if not (exact_path source) then Paths.empty
          else must_paths limited state.must source
        in
        let possible_sources = may_paths limited state source in
        let connect targets sources edges =
          Paths.fold
            (fun target edges ->
              Paths.fold
                (fun source edges ->
                  if Paths.exists (fun slot -> overlaps slot source) possible
                  then edges
                  else add_edge limited target source edges)
                sources edges)
            targets edges
        in
        {
          must = connect definite certain_sources after.must;
          may = connect possible possible_sources after.may;
          limited = !limited;
        }
  in
  ({ writing with limited = !limited }, { after with limited = !limited })

let forget state target = snd (assignment state ~target ~source:None)

let copy_reference ~before ~replaced state ~target ~source =
  let limited = ref (before.limited || state.limited) in
  let overwritten = may_paths ~slot:true limited before replaced in
  let retained path =
    not (Paths.exists (fun slot -> overlaps slot path) overwritten)
  in
  let certain_sources =
    if List.exists (function Taint.Oany | Taint.Oslice _ -> true | _ -> false) (snd source @ snd target) then Paths.empty
    else must_paths limited before.must source |> Paths.filter retained
  in
  let possible_sources =
    may_paths limited before source |> Paths.filter retained
  in
  let state = forget state target in
  let connect sources edges =
    Paths.fold
      (fun source edges -> add_edge limited target source edges)
      sources edges
  in
  {
    must = connect certain_sources state.must;
    may = connect possible_sources state.may;
    limited = !limited;
  }

type array_change = Prepend of Sequence_length.t | Resize of int option

let array_roots limited state target =
  ((if exact_path target then must_paths limited state.must target else Paths.empty), may_paths limited state target)

let array_endpoint (certain, possible) change path =
  let descendants roots =
    Paths.elements roots
    |> List.filter_map (fun root -> Option.map (fun rest -> root, rest) (suffix root path))
    |> List.sort (fun ((_, left), _) ((_, right), _) -> Int.compare (List.length left) (List.length right)) in
  let map (root, rest) =
    let field value = Some (fst root, snd root @ value) in
    match rest, change with
    | [], _ -> Some path
    | (Taint.Oint index :: rest), Prepend count when index >= 0 && index < 4_294_967_295 ->
        (match Sequence_length.exact_value count with
        | Some count -> field (Taint.Oint (index + count) :: rest)
        | None -> field (Taint.Oslice (index + count.minimum) :: rest))
    | (Taint.Oslice index :: rest), Prepend count ->
        field (Taint.Oslice (index + count.minimum) :: rest)
    | Taint.Oany :: _, Prepend _ -> Some path
    | Taint.Oint index :: _, Resize (Some length) when index >= length && index < 4_294_967_295 -> None
    | Taint.Oslice first :: _, Resize (Some length) when first >= length -> None
    | Taint.Oany :: _, Resize (Some 0) -> None
    | _, Resize _ | _, Prepend _ -> Some path in
  let certainty root rest mapped =
    match rest, change, mapped with
    | [], _, _ -> true
    | (Taint.Oint _ :: _), Prepend count, Some mapped ->
        Option.is_some (Sequence_length.exact_value count) && exact_path mapped
    | (Taint.Oint index :: _), Resize (Some length), _ -> index < length || index >= 4_294_967_295
    | (Taint.Oint _ | Taint.Oany | Taint.Oslice _) :: _, Resize None, _ -> false
    | (Taint.Oany | Taint.Oslice _) :: _, _, _ -> false
    | _, _, _ -> exact_path root in
  match descendants certain with
  | (root, rest) :: _ ->
      let mapped = map (root, rest) in
      Option.to_list mapped, certainty root rest mapped
  | [] ->
      (match descendants possible with
      | [] -> [path], true
      | root :: _ ->
          let mapped = map root in
          let paths = path :: Option.to_list mapped |> List.sort_uniq Path.compare in
          paths, false)

let reindex_array state ~target change =
  let state = close state in
  let limited = ref state.limited in
  let roots = array_roots limited state target in
  let rewrite ~must edges = Edges.fold (fun (left, right) result ->
    let lefts, left_certain = array_endpoint roots change left in
    let rights, right_certain = array_endpoint roots change right in
    if must && not (left_certain && right_certain) then result
    else List.fold_left (fun result left ->
      List.fold_left (fun result right -> add_edge limited left right result) result rights)
      result lefts) edges Edges.empty in
  let must = rewrite ~must:true state.must in
  let may = rewrite ~must:false state.may in
  {must; may; limited = !limited}

let copy_array_element ~before ~array ~change state ~target ~source =
  let before = close before in
  let limited = ref (state.limited || before.limited) in
  let roots = array_roots limited before array in
  let transform path = match change with
    | None -> [path], exact_path path
    | Some change -> array_endpoint roots change path in
  let certain = if exact_path source && exact_path target then must_paths limited before.must source else Paths.empty in
  let possible = may_paths limited before source in
  let connect ~must sources edges = Paths.fold (fun source edges ->
    let sources, certain = transform source in
    if must && not certain then edges
    else List.fold_left (fun edges source -> add_edge limited target source edges) edges sources)
    sources edges in
  {must = connect ~must:true certain state.must;
   may = connect ~must:false possible state.may;
   limited = !limited}

let join left right =
  let left = close left and right = close right in
  let limited = ref (left.limited || right.limited) in
  let may =
    Edges.fold
      (fun (a, b) edges -> add_edge limited a b edges)
      right.may left.may
  in
  { must = Edges.inter left.must right.must; may; limited = !limited }

let filter predicate state =
  let state = close state in
  let keep ((left, _), (right, _)) = predicate left && predicate right in
  {
    state with
    must = Edges.filter keep state.must;
    may = Edges.filter keep state.may;
  }

let to_string state =
  let path (name, offsets) =
    IL.str_of_name name ^ String.concat "" (List.map Taint.show_offset offsets)
  in
  let edges value =
    value |> Edges.elements
    |> List.map (fun (left, right) -> path left ^ "=" ^ path right)
    |> String.concat ";"
  in
  "[MUST ALIASES]" ^ edges state.must ^ "[MAY ALIASES]" ^ edges state.may

let%test_module "alias edge index" =
  (module struct
    let name text =
      IL.{ ident = (text, AST_generic.fake text);
        sid = AST_generic.SId.unsafe_default;
        id_info = AST_generic.empty_id_info (); value_origin = None }

    let path text fields = (name text, fields)
    let edge left right edges = add_edge (ref false) left right edges

    let%test_unit "unrelated components do not consume rewrite work" =
      reset_diagnostics ();
      let left = path "left" [] and right = path "right" [] in
      let edges = ref (edge left right Edges.empty) in
      for index = 1 to 63 do
        edges := edge (path ("a" ^ string_of_int index) [])
            (path ("b" ^ string_of_int index) []) !edges
      done;
      let state = { must = !edges; may = !edges; limited = false } in
      for _ = 1 to 20_000 do
        let related, updated = related ~certain:true state left in
        assert (not (is_limited updated));
        assert (List.length related = 2)
      done;
      assert (List.is_empty (take_diagnostics ()))

    let%test_unit "closing disjoint components uses the edge bound" =
      reset_diagnostics ();
      let edges = ref Edges.empty in
      for index = 1 to 200 do
        edges := edge (path ("left" ^ string_of_int index) [])
          (path ("right" ^ string_of_int index) []) !edges
      done;
      let state = close {must = !edges; may = !edges; limited = false} in
      assert (not state.limited);
      assert (Edges.cardinal state.must = 200);
      let values, state = related ~certain:true state (path "left200" []) in
      assert (List.length values = 2 && not state.limited);
      assert (List.is_empty (take_diagnostics ()))

    let%test_unit "a large connected component remains bounded" =
      reset_diagnostics ();
      let edges = ref Edges.empty in
      for index = 1 to 130 do
        edges := edge (path "root" []) (path ("child" ^ string_of_int index) []) !edges
      done;
      let values, state = related ~certain:true {must = !edges; may = !edges; limited = false}
        (path "root" []) in
      assert (List.length values <= max_paths && state.limited);
      assert (not (List.is_empty (take_diagnostics ())))

    let%test_unit "cached rewrites distinguish replacement edges" =
      reset_diagnostics ();
      let a = path "a" [] and b = path "b" [] and c = path "c" [] in
      let query edges = fst (related ~certain:true {must = edges; may = edges; limited = false} a) in
      let first = edge a b Edges.empty and second = edge a c Edges.empty in
      let values = query first in
      let remaining = !(Domain.DLS.get rewrites) in
      assert (List.exists (equal_path b) values);
      assert (List.exists (equal_path b) (query first));
      assert (!(Domain.DLS.get rewrites) = remaining);
      let values = query second in
      assert (List.exists (equal_path c) values);
      assert (not (List.exists (equal_path b) values))

    let%test_unit "the edge bound still reports incompleteness" =
      reset_diagnostics ();
      let limited = ref false and edges = ref Edges.empty in
      for index = 1 to max_edges + 1 do
        edges := add_edge limited (path ("left" ^ string_of_int index) [])
          (path ("right" ^ string_of_int index) []) !edges
      done;
      assert (!limited && Edges.cardinal !edges = max_edges);
      assert (not (List.is_empty (take_diagnostics ())))

    let%test_unit "indexed rewriting agrees with exhaustive edge rewriting" =
      reset_diagnostics ();
      let a = path "a" [] and b = path "b" [] in
      let field = Taint.Ostr "child" in
      let edges = Edges.empty
        |> edge a (path "b" [field])
        |> edge b (path "c" [Taint.Oany])
        |> edge (path "a" [field]) (path "a" [])
        |> edge (path "unrelated" []) (path "other" []) in
      List.iter (fun possible ->
        List.iter (fun slot ->
          List.iter (fun path ->
            let expected = ref Paths.empty and actual = ref Paths.empty in
            Edges.fold (fun (left, right) () ->
              Option.iter (fun value -> expected := Paths.add value !expected)
                (substitute ~slot ~possible left right path);
              Option.iter (fun value -> expected := Paths.add value !expected)
                (substitute ~slot ~possible right left path)) edges ();
            rewrite ~slot ~possible (ref false) edges path
              (fun value -> actual := Paths.add value !actual);
            assert (Paths.equal !expected !actual))
            [a; b; path "a" [field; field]; path "c" [Taint.Ostr "value"];
             path "absent" []]) [false; true]) [false; true]

    let%test_unit "edge filtering and intersection keep the index coherent" =
      reset_diagnostics ();
      let a = path "a" [] and b = path "b" [] and c = path "c" [] in
      let initial = Edges.empty |> edge a b |> edge b c in
      let retained = Edges.filter (fun (left, _) -> equal_path left a) initial in
      let intersection = Edges.inter initial retained in
      List.iter (fun edges ->
        let values = must_paths (ref false) edges a in
        assert (Paths.cardinal values = 2);
        assert (not (Paths.mem c values));
        let visited = ref 0 in
        Edges.iter_root (fst c) (fun _ -> incr visited) edges;
        assert (!visited = 0)) [retained; intersection]
  end)

let%test_unit "alias limit recovers a temporary's source expression" =
  reset_diagnostics ();
  let location = Tok.{ str = "source";
    pos = Pos.make ~line:7 ~column:2 (Fpath.v "alias-limit.js") 41 } in
  let origin = AST_generic.e (AST_generic.N
    (AST_generic.Id (("source", Tok.tok_of_loc location),
      AST_generic.empty_id_info ()))) in
  let temporary = IL.{ ident = ("_tmp", AST_generic.fake "_tmp");
    sid = AST_generic.SId.unsafe_default;
    id_info = AST_generic.empty_id_info (); value_origin = Some origin } in
  record_limit (temporary, []);
  match take_diagnostics () with
  | [Some actual] -> assert (Tok.equal_location actual location)
  | _ -> assert false

let%test_unit "alias limit upgrades missing location without moving a valid one" =
  reset_diagnostics ();
  let location = Tok.{ str = "value";
    pos = Pos.make ~line:11 ~column:4 (Fpath.v "alias-limit.js") 80 } in
  let temporary = IL.{ ident = ("_tmp", AST_generic.fake "_tmp");
    sid = AST_generic.SId.unsafe_default;
    id_info = AST_generic.empty_id_info (); value_origin = None } in
  let located = { temporary with ident = ("value", Tok.tok_of_loc location) } in
  record_limit (temporary, []);
  record_limit (located, []);
  record_limit (temporary, []);
  match take_diagnostics () with
  | [Some actual] -> assert (Tok.equal_location actual location)
  | _ -> assert false
