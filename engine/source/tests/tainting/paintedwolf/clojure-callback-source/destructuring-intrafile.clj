(register (fn [[first second]]
  ;; ruleid: flow
  (sink first)
  ;; ruleid: flow
  (sink second)))
(register (fn [{:keys [query missing] :as request}]
  ;; ruleid: flow
  (sink query)
  ;; ruleid: flow
  (sink missing)
  ;; ruleid: flow
  (sink (:other request))))
