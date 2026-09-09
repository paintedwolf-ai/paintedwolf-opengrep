(register (fn [request ignored]
  (sink (:query request))))
(register (fn
  ([request]
    ;; ruleid: flow
    (sink (:query request)))
  ([request ignored]
    (sink (:query request)))
  ([request success failure]
    ;; ruleid: flow
    (sink (:query request))
    (sink (:query success)))))
(defn multi-handler
  ([request]
    ;; ruleid: flow
    (sink (:query request)))
  ([request ignored]
    (sink (:query request)))
  ([request success failure]
    ;; ruleid: flow
    (sink (:query request))
    (sink (:query failure))))
(register multi-handler)
