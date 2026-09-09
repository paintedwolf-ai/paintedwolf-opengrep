(ns app (:require [library :rename {f assoc}]))
(defn call-external []
  ;; ruleid: flow
  (sink (assoc (source) :query "fixed")))
