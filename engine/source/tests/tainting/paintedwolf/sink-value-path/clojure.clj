(defn queries [flag]
  ;; ruleid: flow
  (sink [(source) "bound"])
  (sink ["SELECT ?" (source)])
  (let [query [(source) "bound"]]
    ;; ruleid: flow
    (sink query))
  (let [query ["SELECT ?" (source)]] (sink query))
  (let [query [(source) "bound"] alias query]
    ;; ruleid: flow
    (sink alias))
  (let [query ["SELECT ?" (source)] query (assoc query 0 (source))]
    ;; ruleid: flow
    (sink query))
  (let [query [(source) "bound"] query (assoc query 0 "SELECT ?")]
    (sink query))
  (let [query (if flag [(source) "bound"] ["SELECT ?" (source)])]
    ;; ruleid: flow
    (sink query))
  (let [value (source)]
    ;; ruleid: flow
    (sink value))
  (sink [])
  (sink ["fixed" [(source)]])
  ;; ruleid: flow
  (sink [[(source)] "fixed"]))
