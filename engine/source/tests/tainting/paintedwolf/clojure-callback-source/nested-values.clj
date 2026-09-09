(defn nested [[first second]]
  ;; ruleid: flow
  (sink first)
  (sink second))
(nested [(source) "fixed" "extra"])
