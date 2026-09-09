(defn handler [value]
;; ok: closure-context
 (let [helper (fn [] value)] (sink (helper "safe"))))
(register handler)
