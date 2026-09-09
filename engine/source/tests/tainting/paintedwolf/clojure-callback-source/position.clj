(register (fn [first request]
  (sink (:query first))
  ;; ruleid: flow
  (sink (:query request))))
(register (fn [first] (sink (:query first))))
