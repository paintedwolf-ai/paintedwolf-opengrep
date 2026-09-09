(defn handler [value]
;; ok: closure-context
 (let [helper (fn [a b] a)] (sink (helper value))))
(register handler)
