(ns app (:require [ring.adapter.jetty] [clojure.java.shell] [next.jdbc]))
(ring.adapter.jetty/run-jetty
  (fn [request]
    (let [request (assoc request :query-params {"input" "fixed"})
          input (get (:query-params request) "input")]
      (clojure.java.shell/sh "sh" "-c" input))) {:port 8080})
