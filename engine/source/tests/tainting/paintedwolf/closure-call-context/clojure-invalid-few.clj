(defn handler [value]
;; ok: closure-context
 (let [helper (fn [a b] value)] (sink (helper "safe"))))
(register handler)
