;; ruleid: flow
(sink {:root (source) :body "safe"})
(sink {:root "/srv/public" :body (source)})
(let [options {:root (source)}]
  ;; ruleid: flow
  (sink options)
  (let [safe (assoc options :root "/srv/public")]
    (sink safe))
  ;; ruleid: flow
  (sink options))
(let [options {:root (source)}
      safe (assoc options :body (:root options) :root "/srv/public")]
  (sink safe))
;; ruleid: flow
(sink (source))
(sink {"root" (source) :root "/srv/public"})
