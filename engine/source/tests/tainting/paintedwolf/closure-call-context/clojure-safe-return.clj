(defn handler [value]
;; ok: closure-context
 (let [helper (fn [& args] "safe")] (sink (helper value))))
(register handler)
