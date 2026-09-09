(ns app (:refer-clojure :exclude [assoc get]))
(defn call-external []
  ;; ruleid: flow
  (sink (assoc (source) :query "fixed")))
