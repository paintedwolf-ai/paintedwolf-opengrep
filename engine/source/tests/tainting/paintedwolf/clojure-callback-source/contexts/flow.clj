(defn handler
  ([request]
    ;; ruleid: flow
    (sink (:query request))
    (sink (:other request)))
  ([request success failure]
    (sink (:query request))
    ;; ruleid: flow
    (sink (:other request))))
(register handler)
