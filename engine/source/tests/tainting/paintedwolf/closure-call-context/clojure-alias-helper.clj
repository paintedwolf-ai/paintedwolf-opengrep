(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn [ignored] value) alias helper] (sink (alias "safe"))))
(register handler)
