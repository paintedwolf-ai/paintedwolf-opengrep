(register (fn [request ignored]
  ;; ruleid: flow
  (sink (:query request))
  (sink (:query ignored))))
(register (fn
  ([request]
    ;; ruleid: flow
    (sink (:query request)))
  ([request ignored]
    ;; ruleid: flow
    (sink (:query request)))))
