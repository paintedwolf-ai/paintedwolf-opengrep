(defn handler [request]
  ;; ruleid: flow
  (sink (:query request))
  (sink (:other request)))
(dispatch (source) handler)
(defn quiet [request] (sink (:query request)))
(dispatch "fixed" quiet)
