(defn handler [value]
;; ok: closure-context
 (let [helper (fn [a] a)] (sink (helper value "extra"))))
(register handler)
