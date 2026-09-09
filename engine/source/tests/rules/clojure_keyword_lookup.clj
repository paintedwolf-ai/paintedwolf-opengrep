;; ruleid: keyword-source
(sink (:input request))
;; ok: keyword-source
(sink (:other request))
(let [value (:input request)]
  ;; ruleid: keyword-source
  (sink value))
;; ruleid: keyword-source
(sink (:input request "fallback"))
(defn handler [request]
  ;; ruleid: keyword-source
  (sink (:input request)))
;; ok: keyword-source
'(sink (:input request))
;; ok: keyword-source
"(sink (:input request))"
;; ok: keyword-source
(sink "fixed")
