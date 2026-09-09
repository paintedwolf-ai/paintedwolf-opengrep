(register (fn [request]
  ;; ruleid: flow
  (sink (:query request))))
(defn handler [request]
  ;; ruleid: flow
  (sink (:query request)))
(register handler)
(let [handler (fn [request]
  ;; ruleid: flow
  (sink (:query request)))]
  (register handler))
(register (fn [request success failure]
  ;; ruleid: flow
  (sink (:query request))
  (sink (:query success))
  (sink (:query failure))))
(defn unregistered [request] (sink (:query request)))
