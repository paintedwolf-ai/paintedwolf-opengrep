(ns app (:refer-clojure :exclude [assoc]))
(declare assoc)
(defn forward-shadow []
  ;; ruleid: flow
  (sink (:query (assoc {:query (source)} :query "fixed"))))
(defn assoc [value key replacement] value)
