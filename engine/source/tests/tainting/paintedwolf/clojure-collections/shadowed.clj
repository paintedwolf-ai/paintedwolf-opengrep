(ns app)
(defn assoc [value key replacement] value)
(defn named-shadow []
  ;; ruleid: flow
  (sink (assoc (source) :query "fixed")))
