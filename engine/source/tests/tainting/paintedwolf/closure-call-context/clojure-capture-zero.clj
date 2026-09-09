(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn [] value)] (sink (helper))))
(register handler)
