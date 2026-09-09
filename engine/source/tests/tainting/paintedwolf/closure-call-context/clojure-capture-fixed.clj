(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn [ignored] value)] (sink (helper "safe"))))
(register handler)
