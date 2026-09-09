(defn handler [request]
  ;; ruleid: flow
  (sink request)
  (let [request "fixed"] (sink request)))
(register handler)
