(defn handler [value]
;; ok: closure-context
 (let [helper (fn ([] "safe") ([ignored] value))] (sink (helper))))
(register handler)
