(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn ([] "safe") ([ignored] value))] (sink (helper "safe"))))
(register handler)
