(ns app (:require [ring.adapter.jetty :as server] [ring.middleware.params :as params]))
(server/run-jetty
  (params/wrap-params
    (fn [request]
      (let [code (get (:query-params request) "code")]
        ;; ruleid: lycaon.clojure.ring-code-injection
        (clojure.core/load-string code))))
  {:port 8080})
(server/run-jetty
  (params/wrap-params
    (fn [request]
      (let [incoming request code (get (:query-params incoming) "code")]
        ;; ruleid: lycaon.clojure.ring-code-injection
        (clojure.core/load-string code))))
  {:port 8081})
(server/run-jetty
  (params/wrap-params
    (fn [request]
      (let [request {:query-params {"code" "(+ 1 2)"}} code (get (:query-params request) "code")]
        (clojure.core/load-string code))))
  {:port 8082})
(server/run-jetty
  (params/wrap-params
    (fn [request]
      (clojure.core/load-string "(+ 1 2)")))
  {:port 8083})
(server/run-jetty
  (params/wrap-params
    (fn [request]
      (let [{:strs [code]} (:query-params request)]
        ;; ruleid: lycaon.clojure.ring-code-injection
        (clojure.core/load-string code))))
  {:port 8084})
(server/run-jetty
  (params/wrap-params
    (fn [request]
      ;; ruleid: lycaon.clojure.ring-code-injection
      (-> request :query-params (get "code") clojure.core/load-string)))
  {:port 8085})
