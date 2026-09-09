(defn handler [request]
  ;; ruleid: flow
  (sink (:query request))
  (sink (:other request)))
(let [alias handler] (register alias))
(defn quiet-handler [request] (sink (:query request)))
(let [quiet-handler (fn [request] "fixed")]
  (register quiet-handler))
(let [handler (fn [request]
    ;; ruleid: flow
    (sink (:query request)))
      table {:run handler}]
  (register (get table :run)))
(register (fn [{:keys [query other]}]
  ;; ruleid: flow
  (sink query)
  (sink other)))
(register (fn [request]
  (let [request {:query "fixed"}]
    (sink (:query request)))))
