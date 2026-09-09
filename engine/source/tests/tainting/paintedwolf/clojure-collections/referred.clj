(ns app (:require [library :refer [assoc get]]))
(defn call-external []
  ;; ruleid: flow
  (sink (assoc (source) :query "fixed")))
