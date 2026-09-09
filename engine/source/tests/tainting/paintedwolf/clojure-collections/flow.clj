(ns app (:require [clojure.core :as core]))
(defn collections [key]
  (let [original {:query (source) :safe "fixed"}
        revised (assoc original :query "fixed")]
    (sink (:query revised))
    ;; ruleid: flow
    (sink (:query original))
    (sink (get revised :safe))
    (sink (get revised :query)))
  (let [original {:query "fixed" :safe "fixed"}
        revised (assoc original :query (source))]
    ;; ruleid: flow
    (sink (get revised :query))
    (sink (get original :query))
    (sink (:safe revised)))
  (let [original [(source) "fixed"] revised (core/assoc original 0 "fixed")]
    (sink (core/get revised 0))
    ;; ruleid: flow
    (sink (core/get original 0)))
  (let [original {:query (source)} revised (clojure.core/assoc original :query "fixed")]
    (sink (clojure.core/get revised :query)))
  (let [original {:query "fixed"} revised (assoc original key (source))]
    ;; ruleid: flow
    (sink (:query revised)))
  (let [original {:query "fixed"} revised (assoc original :query (source) :query "fixed")]
    (sink (:query revised)))
  (let [assoc (fn [value key replacement] value)
        original {:query (source)} revised (assoc original :query "fixed")]
    ;; ruleid: flow
    (sink (:query revised)))
  (let [get (fn [value key] (:unsafe value))]
    ;; ruleid: flow
    (sink (get {:query "fixed" :unsafe (source)} :query))))

(defn unknown-collection []
  (let [original (source) revised (assoc original :query "fixed")]
    (sink (:query revised))
    ;; ruleid: flow
    (sink (:other revised))
    ;; ruleid: flow
    (sink (:query original))))

(defn nested-overwrite []
  (let [original (source) revised (assoc original :query {"input" "fixed"})]
    (sink (get (:query revised) "input"))))
